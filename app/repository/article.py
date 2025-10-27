from pprint import pprint
from typing import List

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

    async def get_articles_by_local_vendor_codes(self, local_vendor_codes: list[str]) -> list[int]:
        """Получить все nm_id для списка local_vendor_code."""
        query = """
            SELECT nm_id
            FROM article
            WHERE local_vendor_code = ANY($1);
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, local_vendor_codes)

        return [row["nm_id"] for row in rows]


    async def get_accounts_by_articles(self, articles: set[int]) -> dict[str, list[int]]:
        """Получить аккаунты карточек."""
        query = """
            SELECT account, nm_id
            FROM article
            WHERE nm_id = ANY($1)
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, articles)

        accounts = {}

        for row in rows:
            account = row["account"]

            if not account in accounts:
                accounts[account] = []

            accounts[account].append(row["nm_id"])

        return accounts

    async def close_articles_in_account(self, account: str, nm_ids: list[int]):
        """Установить статус 'closed' для карточек аккаунта"""
        query_for_update = """
            SELECT nm_id, status
            FROM card_status
            WHERE account = $1 AND nm_id = ANY($2)
            FOR UPDATE
        """
        query_upsert_status = """
            INSERT INTO card_status (nm_id, account, status, updated_at)
            VALUES ($1, $2, 'closed', NOW())
            ON CONFLICT (nm_id, account)
            DO UPDATE SET status = 'closed', updated_at = NOW()
            WHERE card_status.status != 'closed'
        """
        query_insert_status_log = """
            INSERT INTO card_status_log (nm_id, account, status, changed_at)
            VALUES ($1, $2, 'closed', NOW())
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(query_for_update, account, nm_ids)

                existing = {row['nm_id']: row['status'] for row in rows}

                for nm_id in nm_ids:
                    if existing.get(nm_id) == 'closed':
                        continue

                    await conn.execute(query_upsert_status, nm_id, account)
                    await conn.execute(query_insert_status_log, nm_id, account)

    async def create_clearance_task(self, task_id: str, account: str, nm_ids: list[int]) -> int:
        query = """
            INSERT INTO stock_clearance_task (task_id, account, nm_ids)
            VALUES ($1, $2, $3)
            RETURNING id;
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id, account, nm_ids)
            return row["id"]