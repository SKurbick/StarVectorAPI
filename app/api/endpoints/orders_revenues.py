import datetime
from typing import List

from fastapi import APIRouter, Depends
from app.domain import OrdersRevenues
from app.service import OrdersRevenuesService
from app.dependencies import get_orders_revenues_service

router = APIRouter(tags=["Воронка продаж"])


# @router.get("/orders_revenues", response_model=List[OrdersRevenues])
# async def get_orders_revenues(
#         service: OrdersRevenuesService = Depends(get_orders_revenues_service)
# ):
#     return await service.get_orders_revenues()


@router.get("/orders_revenues/{date}", response_model=List[OrdersRevenues])
async def get_orders_revenues_by_date(
        date: datetime.date,
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
):
    return await service.get_orders_revenues_by_date(date)
