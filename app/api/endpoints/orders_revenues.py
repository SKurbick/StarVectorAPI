from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.domain import OrdersRevenuesResponseModel
from app.domain.models import PeriodRequestModel, WeeklyOrdersResponse, UserPermissions
from app.service import OrdersRevenuesService
from app.dependencies import get_orders_revenues_service, get_info_from_token

router = APIRouter(tags=["Воронка продаж"])

revenues_by_week_description = "1 - текущая неделя. С повышением числа (2, 3 ...) будут учтены в ответе предыдущие недели"


@router.post("/orders_revenues", response_model=List[OrdersRevenuesResponseModel])
async def get_orders_revenues_by_date(
        period: PeriodRequestModel,
        user: UserPermissions = Depends(get_info_from_token),
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
):
    if not user.crm_viewing_unit_economics:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_data_by_period(period)


@router.get("/revenues_by_week")
async def get_last_week_data(
        number_of_last_weeks: int = Query(..., gt=0, le=12, example=1, description=revenues_by_week_description),
        user: UserPermissions = Depends(get_info_from_token),
        service: OrdersRevenuesService = Depends(get_orders_revenues_service)
) -> WeeklyOrdersResponse:
    if not user.crm_viewing_unit_economics:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_last_week_data(number_of_last_weeks)
