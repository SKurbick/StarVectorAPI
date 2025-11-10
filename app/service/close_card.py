from asyncpg import Pool

from app.domain.models import CloseCardsRequest
from app.use_cases.card_use_cases import CloseCardUseCase
from app.infrastructure.WildberriesAPI.marketplace import StockFBWMarketplace


class CloseCardService:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def close_cards(self, data: CloseCardsRequest):
        card_closer = CloseCardUseCase(
            pool=self.pool
        )

        result = await card_closer.execute(data)
        return result

    async def close_cards_preview(self, data: CloseCardsRequest):
        stock_movement_fetcher = StockFBWMarketplace()

        target_data = {}

        for acc, cards in data.accounts.items():
            if not acc in target_data:
                target_data[acc] = []

            target_data[acc].extend(cards.nm_ids)

        result = await stock_movement_fetcher.get_stock_movement(target_data)

        return result
