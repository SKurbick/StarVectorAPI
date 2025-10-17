from app.repository.competitors_prices import CompetitorsPricesRepository


class CompetitorsPricesService:
    def __init__(self, repository: CompetitorsPricesRepository):
        self.repository = repository

    async def get_competitors_prices(self):
        return await self.repository.get_competitors_prices()
