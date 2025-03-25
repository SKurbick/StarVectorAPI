import datetime
from typing import List

from app.repository import StocksQuantityRepository
from app.domain.models import StocksQuantity


class StocksQuantityService:
    def __init__(self, stocks_quantity: StocksQuantityRepository):
        self.stocks_quantity = stocks_quantity

    async def get_all_data(self) -> List[StocksQuantity]:
        return await self.stocks_quantity.get_all_data()

    # async def get_orders_revenues(self) -> List[OrdersRevenues]:  # todo решить за какое время
    #     return await self.orders_revenues_repository.get_orders_revenues()
