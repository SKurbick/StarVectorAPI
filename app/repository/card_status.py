from asyncpg import Pool


class CardStatusRepository:
    """
    Репозиторий для управления статусами карточек товаров.
    """

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_status_by_nm_ids(self, nm_ids: list[int]) -> dict[int, str]:
        """
        Возвращает {nm_id: status} для существующих записей в card_status.
        Если запись отсутствует — nm_id не будет в результате (считается 'active').
        """
        if not nm_ids:
            return {}

        query = "SELECT nm_id, status FROM card_status WHERE nm_id = ANY($1)"
        rows = await self.pool.fetch(query, nm_ids)

        return {row["nm_id"]: row["status"] for row in rows}
