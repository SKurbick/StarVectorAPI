import datetime
from typing import List

from app.repository import OrdersRevenuesRepository
from app.domain.models import OrdersRevenues, PeriodRequestModel, OrdersRevenuesResponseModel


class OrdersRevenuesService:
    def __init__(self, orders_revenues_repository: OrdersRevenuesRepository):
        self.orders_revenues_repository = orders_revenues_repository

    async def get_data_by_period(self, period: PeriodRequestModel) -> List[OrdersRevenuesResponseModel]:
        return await self.orders_revenues_repository.get_data_by_period(period)

    # async def get_orders_revenues(self) -> List[OrdersRevenues]:  # todo решить за какое время
    #     return await self.orders_revenues_repository.get_orders_revenues()
