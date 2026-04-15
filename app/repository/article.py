from typing import List, Optional

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
            ), FeedbackCounts AS (
                SELECT
                    nmid AS article_id,
                    COUNT(*) AS reviews_count
                FROM wb_feedbacks
                GROUP BY nmid
            )
            SELECT
                a.account,
                lcp.purchase_price,
                lcp.status_by_lvc,
                a.local_vendor_code,
                cd.article_id,
                cd.barcode,
                cd.subject_name,
                cd.photo_link,
                cd.length,
                cd.width,
                cd.height,
                cd.rating,
                COALESCE(fc.reviews_count, 0) AS reviews_count,
                cd.manager,
                cd.local_card_name,
                cd.chrt_id,
                crfs.stocks_quantity,
                pn.note
            FROM
                article a
            LEFT JOIN
                LatestCostPrice lcp
                ON a.local_vendor_code = lcp.local_vendor_code
            INNER JOIN
                card_data cd
                ON a.nm_id = cd.article_id
            LEFT JOIN
                current_real_fbs_stocks_qty crfs
                ON a.local_vendor_code = crfs.local_vendor_code
            LEFT JOIN product_notes pn
            	on a.nm_id = pn.nm_id and a.account = pn.account and a.local_vendor_code = pn.local_vendor_code
            LEFT JOIN FeedbackCounts fc
                ON fc.article_id = a.nm_id;
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

    async def get_articles_by_criteria(
        self,
        nm_ids_by_account: Optional[dict[str, list[int]]] = None,
        local_vendor_codes: Optional[list[str]] = None,
    ) -> tuple[list[dict], list[int], list[str]]:
        """
        Возвращает кортеж:
            - список словарей с данными по карточке dict('nm_id', 'account', 'local_vendor_code'),
            - ненайденные артикулы,
            - ненайденные local_vendor_code
        """
        if not nm_ids_by_account and not local_vendor_codes:
            return [], [], []

        all_requested_nm_ids: set[int] = set()
        all_requested_lvc: set[str] = set()

        if nm_ids_by_account:
            for nm_list in nm_ids_by_account.values():
                all_requested_nm_ids.update(nm_list)

        if local_vendor_codes:
            all_requested_lvc.update(local_vendor_codes)


        where_clauses = []
        params = []
        param_idx = 1

        if nm_ids_by_account:
            account_nm_pairs = []

            for account, nm_list in nm_ids_by_account.items():
                for nm in nm_list:
                    account_nm_pairs.append((account, nm))

            if account_nm_pairs:
                placeholders = ", ".join(f"(${i*2+1}, ${i*2+2})" for i in range(len(account_nm_pairs)))
                where_clauses.append(f"(account, nm_id) IN ({placeholders})")

                for acc, nm in account_nm_pairs:
                    params.extend([acc, nm])

                param_idx += len(account_nm_pairs) * 2

        if local_vendor_codes:
            if where_clauses:
                where_clauses.append("OR")

            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(local_vendor_codes)))
            where_clauses.append(f"local_vendor_code = ANY(ARRAY[{placeholders}])")
            params.extend(local_vendor_codes)
            param_idx += len(local_vendor_codes)

        query = """
            SELECT
                nm_id, account, local_vendor_code 
            FROM article
            WHERE nm_id NOT IN (
                SELECT nm_id
                FROM banned_products
            )
        """

        if where_clauses:
            query += " AND (" + " ".join(where_clauses) + ")"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        found_articles = [
            {"nm_id": r["nm_id"], "account": r["account"], "local_vendor_code": r["local_vendor_code"]}
            for r in rows
        ]

        found_nm_ids = {r["nm_id"] for r in found_articles}
        found_lvc = {r["local_vendor_code"] for r in found_articles if r["local_vendor_code"]}

        invalid_nm_ids = list(all_requested_nm_ids - found_nm_ids)
        invalid_lvc = list(all_requested_lvc - found_lvc)

        return found_articles, invalid_nm_ids, invalid_lvc

    async def get_article_by_nm_id_and_account(self, nm_id: int, account: str):
        query = """
        SELECT
            a.nm_id,
            a.account,
            a.vendor_code,
            a.local_vendor_code,
            a.created_at
        FROM article a
        WHERE a.nm_id = $1 AND a.account = $2
        """

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, nm_id, account.upper())

    async def get_vendor_codes_by_local_and_account(self, local_vendor_code: str, account: str) -> list[str]:
        query = """
            SELECT
                a.vendor_code
            FROM article a
            WHERE a.local_vendor_code = $1 AND account = $2
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, local_vendor_code, account.upper())

        return [row["vendor_code"] for row in rows]

    async def create_article(
        self,
        nm_id: int,
        account: str,
        vendor_code: str,
        local_vendor_code: str
    ):
        query = """
        INSERT INTO article (nm_id, account, vendor_code, local_vendor_code)
        VALUES ($1, $2, $3, $4)
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    query,
                    nm_id,
                    account.upper(),
                    vendor_code,
                    local_vendor_code,
                )

    async def update_article(
        self,
        nm_id: int,
        account: Optional[str] = None,
        vendor_code: Optional[str] = None,
        local_vendor_code: Optional[str] = None
    ):
        query = """
        UPDATE article
        SET
        """
        params = []
        set_conditions = []

        if account:
            set_conditions.append(f"account = ${len(params) + 1}")
            params.append(account.upper())

        if vendor_code:
            set_conditions.append(f"vendor_code = ${len(params) + 1}")
            params.append(vendor_code)

        if local_vendor_code:
            set_conditions.append(f"local_vendor_code = ${len(params) + 1}")
            params.append(local_vendor_code)

        if not params:
            raise ValueError("Нет параметров для обновления таблицы article")

        full_query = query + " " + ", ".join(set_conditions) + f" WHERE nm_id = ${len(params) + 1}"

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    full_query,
                    *params,
                    nm_id,
                )

    async def delete_article(
        self,
        nm_id: int,
        account: str,
    ):
        query =  """
            DELETE FROM article
            WHERE
                nm_id = $1
                AND account = $2
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, nm_id, account.upper())
