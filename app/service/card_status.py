from app.repository.card_status import CardStatusRepository


class CardStatusService:
    def __init__(self, repository: CardStatusRepository):
        self.repository = repository

    async def get_stocks_editable_barcodes(self, barcodes: list[str]) -> tuple[list[str], list[str]]:
        """
        Принимает список баркодов.
        Возвращает кортеж: (разрешённые, запрещённые).
        """
        return await self.repository.get_stocks_editable_barcodes(barcodes)
