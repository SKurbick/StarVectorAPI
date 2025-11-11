from asyncpg import Pool

from app.domain.models import CloseCardsRequest
from app.use_cases.card_use_cases import CloseCardUseCase
from app.service.stock_movement import StockMovementService
from app.repository.article import ArticleRepository


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
        stock_movement_fetcher = StockMovementService()
        article_repo = ArticleRepository(self.pool)

        target_data = {}

        if data.accounts:
            for acc, cards in data.accounts.items():
                if not acc in target_data:
                    target_data[acc] = []

                target_data[acc].extend(cards.nm_ids)

        if data.local_vendor_codes:
            found, not_found = await article_repo.get_articles_by_local_vendor_codes(data.local_vendor_codes)

            lvc_nm_ids = [nm for lvc, nms in found.items() for nm in nms]
            lvc_nm_ids_by_acc = await article_repo.get_accounts_by_nm_ids(lvc_nm_ids)

            for acc, nms in lvc_nm_ids_by_acc.items():
                if not acc in target_data:
                    target_data[acc] = []

                target_data[acc].extend(nms)

        result = await stock_movement_fetcher.get_stock_movement(target_data)

        if not_found:
            result["not_found_lvc"] = not_found

        return result
