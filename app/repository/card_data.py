from typing import List

from asyncpg import Pool
from app.domain.models import CardData


class CardDataRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_card_data_by_article_id(self, article_id: int) -> CardData:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM card_data WHERE article_id = $1", article_id)
            return CardData(**row) if row else None

    async def get_all_card_data(self) -> List[CardData]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM card_data ")

            return [CardData(**row) for row in rows]

    async def get_article_ids_by_barcodes(self, barcodes: dict[str, list[str]]) -> dict[str, dict[str, int]]:
        """
        Возвращает nm_id карточек с баркодами, сгруппированные по аккаунтам.
        Баркоды, не найденные в БД, отсутствуют в результате.
        """
        where_conditions = []
        params = []

        for acc, skus in barcodes.items():
            if not skus:
                continue

            where_conditions.append(
                f"(a.account = ${len(params) + 1} AND cd.barcode = ANY(${len(params) + 2}))"
            )
            params.extend((acc.upper(), skus))

        if not where_conditions:
            return {}

        query = """
            SELECT a.account, cd.article_id, cd.barcode
            FROM card_data cd
            LEFT JOIN article a ON a.nm_id = cd.article_id
        """

        query += " WHERE " + " OR ".join(where_conditions)
        query += " ORDER BY a.account, cd.article_id, cd.barcode"

        rows = await self.pool.fetch(query, *params)

        result = {}

        for row in rows:
            account = row["account"]

            if not account in result:
                result[account] = {}

            result[account][row["barcode"]] = row["article_id"]

        return result

    async def create_card_data(self, data):
        query = """
        INSERT INTO card_data (
            article_id, barcode, height, length, width,
            weight_brutto, subject_name, last_update_time, chrt_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (article_id) DO UPDATE 
        SET height = EXCLUDED.height,
            length = EXCLUDED.length,
            width = EXCLUDED.width,
            weight_brutto = EXCLUDED.weight_brutto,                
            subject_name = EXCLUDED.subject_name,
            last_update_time = EXCLUDED.last_update_time,
            chrt_id = EXCLUDED.chrt_id
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(query, data)

    async def get_chrt_ids_by_article_ids(self, article_ids: list[int]) -> dict[int, int]:
        """
        Возвращает словарь с nm_id карточек и chrt_id.
        """
        if not article_ids:
            return {}
    
        query = """
        SELECT article_id, chrt_id
        FROM card_data
        WHERE article_id = ANY($1)
        """

        rows = await self.pool.fetch(query, article_ids)
        return {row["article_id"]: row["chrt_id"] for row in rows}
