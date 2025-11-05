from typing import List, Any

from asyncpg import Pool
from pydantic import ValidationError

from app.domain.models import ArticleDetails


class ArticleRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_article_details(self) -> List[ArticleDetails]:
        async with self.pool.acquire() as conn:
            query = """
            WITH LatestCostPrice AS (
                SELECT
                    local_vendor_code,
                    purchase_price,
                    status_by_lvc,
                    created_at
                FROM (
                    SELECT
                        local_vendor_code,
                        purchase_price,
                        status_by_lvc,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY local_vendor_code
                            ORDER BY created_at DESC
                        ) AS rn
                    FROM cost_price
                ) t
                WHERE rn = 1
            )
            SELECT
                a.account,
                lcp.purchase_price,
                lcp.status_by_lvc,
                lcp.local_vendor_code,
                -- Явно перечисляем нужные поля из card_data вместо cd.*
                cd.article_id,
                cd.barcode,
                cd.article_id,
                cd.subject_name,
                cd.photo_link,
                cd.length,
                cd.width,
                cd.height,
                cd.barcode,
                cd.rating,
                cd.manager,
                cd.local_card_name,
                -- Добавляем остальные нужные поля из card_data...
                crfs.stocks_quantity
            FROM
                article a
            INNER JOIN
                LatestCostPrice lcp
                ON a.local_vendor_code = lcp.local_vendor_code
            INNER JOIN
                card_data cd
                ON a.nm_id = cd.article_id
            LEFT JOIN
                current_real_fbs_stocks_qty crfs
                ON a.local_vendor_code = crfs.local_vendor_code;
                            """
            rows = await conn.fetch(query)
            result = []
            for row in rows:
                try:
                    # Преобразуем row в словарь
                    row_dict = dict(row)

                    # Создаем экземпляр плоской модели
                    flat_article_details = ArticleDetails.model_validate(row_dict)

                    result.append(flat_article_details)

                except ValidationError as e:
                    # Логируем ошибку валидации и пропускаем текущую строку
                    print(f"Validation error for row {row}: {e}")
                    continue

            return result

    async def get_articles_by_local_vendor_codes(
        self, local_vendor_codes: list[str]
    ) -> tuple[dict[str, list[int]], list[str]]:
        """
        Возвращает:
            - словарь: local_vendor_code → список nm_id (может быть пустым, но обычно 1),
            - список local_vendor_code, для которых не найдено ни одного nm_id.
        """
        if not local_vendor_codes:
            return {}, []

        query = """
            SELECT local_vendor_code, nm_id
            FROM article
            WHERE local_vendor_code = ANY($1)
            ORDER BY local_vendor_code;
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, local_vendor_codes)

        found = {}

        for row in rows:
            code = row["local_vendor_code"]
            if code not in found:
                found[code] = []
            found[code].append(row["nm_id"])

        not_found = [code for code in local_vendor_codes if code not in found]

        return found, not_found
    
    async def check_nm_ids_exist(self, nm_ids: list[int]) -> tuple[set[int], set[int]]:
        """Возвращает (найденные_nm_ids, не_найденные_nm_ids)."""
        if not nm_ids:
            return set(), set()

        query = "SELECT nm_id FROM article WHERE nm_id = ANY($1)"
        rows = await self.pool.fetch(query, nm_ids)
        found = {row["nm_id"] for row in rows}
        not_found = set(nm_ids) - found

        return list(found), list(not_found)

    async def get_accounts_by_nm_ids(self, nm_ids: list[int]) -> dict[str, list[int]]:
        """Возвращает словарь: account → [nm_id, ...]"""
        if not nm_ids:
            return {}

        query = """
            SELECT account, nm_id
            FROM article
            WHERE nm_id = ANY($1)
            ORDER BY account
        """

        rows = await self.pool.fetch(query, nm_ids)
        result = {}

        for row in rows:
            acc = row["account"]

            if acc not in result:
                result[acc] = []

            result[acc].append(row["nm_id"])

        return result
