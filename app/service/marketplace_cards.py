from app.infrastructure.marketplace_cards_api import MarketplaceCardsAPI


class MarketplaceCardsService:
    def __init__(self, marketplace_cards_api: MarketplaceCardsAPI):
        self._cards_api = marketplace_cards_api

    async def get_vat(self) -> list[str]:
        return await self._cards_api.get_vat()

    async def get_brands(self, subject_id: int, limit: int = 1, offset: int = 0):
        return await self._cards_api.get_brands(subject_id, limit, offset)

    async def get_seasons(self):
        return await self._cards_api.get_seasons()

    async def get_countries(self):
        return await self._cards_api.get_countries()

    async def get_kinds(self):
        return await self._cards_api.get_kinds()

    async def get_colors(self):
        return await self._cards_api.get_colors()

    async def get_charcs_by_subject_id(self, subject_id: int):
        return await self._cards_api.get_charcs_by_subject_id(subject_id)
    
    async def get_product_cards(self, product_id: str):
        return await self._cards_api.get_product_cards(product_id)
    
    async def get_product_wb_specifications(self, product_id: str):
        return await self._cards_api.get_product_wb_specifications(product_id)

    async def get_subjects_by_filters(self, parent_id: int | None = None):
        return await self._cards_api.get_subjects_by_filters(parent_id)

    async def get_all_categories(self):
        return await self._cards_api.get_all_categories()

    async def get_predifined_charc_ids(self):
        return await self._cards_api.get_predifined_charc_ids()
