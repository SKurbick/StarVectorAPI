import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from app.domain import OrdersRevenuesResponseModel
from app.domain.models import PeriodRequestModel, WeeklyOrdersResponse
from app.service import OrdersRevenuesService
from app.dependencies import get_orders_revenues_service

router = APIRouter(tags=["Воронка продаж"])

revenues_by_week_description = "1 - текущая неделя. С повышением числа (2, 3 ...) будут учтены в ответе предыдущие недели"


@router.post("/orders_revenues", response_model=List[OrdersRevenuesResponseModel])
async def get_orders_revenues_by_date(
        period: PeriodRequestModel,
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
):
    return await service.get_data_by_period(period)


@router.get("/revenues_by_week")
async def get_last_week_data(
        number_of_last_weeks: int = Query(..., gt=0, le=12, example=1, description=revenues_by_week_description),
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
) -> WeeklyOrdersResponse:
    return await service.get_last_week_data(number_of_last_weeks)
