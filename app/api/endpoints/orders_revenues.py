import datetime
from typing import List

from fastapi import APIRouter, Depends
from app.domain import OrdersRevenuesResponseModel
from app.domain.models import PeriodRequestModel
from app.service import OrdersRevenuesService
from app.dependencies import get_orders_revenues_service

router = APIRouter(tags=["Воронка продаж"])


# @router.get("/orders_revenues", response_model=List[OrdersRevenues])
# async def get_orders_revenues(
#         service: OrdersRevenuesService = Depends(get_orders_revenues_service)
# ):
#     return await service.get_orders_revenues()


@router.post("/orders_revenues", response_model=List[OrdersRevenuesResponseModel])
async def get_orders_revenues_by_date(
        period: PeriodRequestModel,
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
):
    return await service.get_data_by_period(period)
