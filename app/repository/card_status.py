from asyncpg import Pool


class CardStatusRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_close_cards_by_nm_ids(self, nm_ids: list[int]) -> list[int]:
        "Получить закрытые карточки"
        query = """
            SELECT nm_id
            FROM card_status
            WHERE nm_id = ANY($1) AND status = 'closed'
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, nm_ids)

        return [row["nm_id"] for row in rows]

    async def close_cards_in_account(self, account: str, nm_ids: list[int]):
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

                existing = {row["nm_id"]: row["status"] for row in rows}

                for nm_id in nm_ids:
                    if existing.get(nm_id) == "closed":
                        continue

                    await conn.execute(query_upsert_status, nm_id, account)
                    await conn.execute(query_insert_status_log, nm_id, account)
