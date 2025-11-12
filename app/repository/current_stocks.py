from asyncpg import Pool


class CurrentStocksRepository:
    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def get_fbs_stocks_by_nm_and_account(
        self,
        nm_account_pairs: list[tuple[int, str]]
    ) -> dict[tuple[int, str], int]:
        if not nm_account_pairs:
            return {}

        unique_nm_ids = list({nm for nm, _ in nm_account_pairs})

        query = f"""
            SELECT article_id, COALESCE(quantity, 0) AS quantity
            FROM current_stocks_quantity
            WHERE article_id = ANY($1)
            AND quantity_type = 'ФБС'
        """

        rows = await self.pool.fetch(query, unique_nm_ids)

        nm_to_stock = {row["article_id"]: row["quantity"] for row in rows}

        result = {}

        for nm_id, account in nm_account_pairs:
            result[(nm_id, account)] = nm_to_stock.get(nm_id, 0)

        return result
