from app.repository.competitors_prices import CompetitorPriceRepository


class CompetitorPriceService:
    def __init__(self, repository: CompetitorPriceRepository):
        self.repository = repository

    async def get_all_competitors_prices(self):
        return await self.repository.get_all_competitors_prices()
