from typing import List

from app.repository.price_discount import PriceDiscountRepository
from app.domain.models import PriceDiscountResponseModel
from app.infrastructure.WildberriesAPI.price_discount import ListOfGoodsPricesAndDiscounts

class CardDataService:
    def __init__(self, price_discount_repository: PriceDiscountRepository):
        self.price_discount_repository = price_discount_repository

    async def update_price_and_discount_data(self, data: PriceDiscountResponseModel) -> ...:

        return await self.price_discount_repository.update_price_and_discount_data(data)

    # async def get_all_card_data(self) -> List[CardData]:
    #     return await self.card_data_repository.get_all_card_data()