from app.repository.card_status import CardStatusRepository


class CardStatusService:
    def __init__(self, repository: CardStatusRepository):
        self.repository = repository

    async def get_status_by_nm_ids(self, nm_ids: list[int]) -> dict[int, str]:
        """
        Возвращает {nm_id: status} для существующих записей в card_status.
        Если запись отсутствует — nm_id не будет в результате (считается 'active').
        """
        return await self.repository.get_status_by_nm_ids(nm_ids)
