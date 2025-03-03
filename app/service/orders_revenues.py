import datetime
from typing import List

from app.repository import OrdersRevenuesRepository
from app.domain.models import OrdersRevenues


class OrdersRevenuesService:
    def __init__(self, orders_revenues_repository: OrdersRevenuesRepository):
        self.orders_revenues_repository = orders_revenues_repository

    async def get_orders_revenues_by_date(self, date: datetime.date) -> List[OrdersRevenues]:
        return await self.orders_revenues_repository.get_data_by_date(date)

    # async def get_orders_revenues(self) -> List[OrdersRevenues]:  # todo решить за какое время
    #     return await self.orders_revenues_repository.get_orders_revenues()
