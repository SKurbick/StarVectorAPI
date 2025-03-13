

import datetime
from typing import List

from app.repository import NetProfitRepository
from app.domain.models import NetProfitResponseModel, PeriodRequestModel


class NetProfitService:
    def __init__(self, net_profit_repository: NetProfitRepository):
        self.net_profit_repository = net_profit_repository

    async def get_net_profit_by_period(self, period: PeriodRequestModel) -> List[NetProfitResponseModel]:
        return await self.net_profit_repository.get_data_by_period(period)

    # async def get_orders_revenues(self) -> List[OrdersRevenues]:  # todo решить за какое время
    #     return await self.orders_revenues_repository.get_orders_revenues()
