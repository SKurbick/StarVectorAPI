from typing import Optional
import datetime
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from app.dependencies.sales_management import get_sales_management_service
from app.domain.models import SalesManagementBaseSummWithDate, ResponseMessage
from app.service.sales_management import SalesManagementService

router = APIRouter(prefix="/sales-management", tags=["Управление продажами"])

# TODO fix naming first two and description info
@router.get("/sales/order", response_model=list[SalesManagementBaseSummWithDate], description="""
    **Получить продажи по категориям за конкретный день**\n
    date: format date, example: 2025-12-18,
    good_category: Optinal row, example 'Казаны' 
""")
async def get_sales_by_date(
        date: datetime.date,
        good_category: Optional[str] = None,
        service: SalesManagementService = Depends(get_sales_management_service)
):

    return await service.get_sum_sales_category_by_date(date, good_category)

@router.get("/sales/orders", description="""
    **Получить продажи по категориям за недельный период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
""")
async def get_weekly_sales_by_date(
        date_start: datetime.date,
        date_end: datetime.date,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    result = await service.get_sum_sales_category_by_period_with_managers(
        start_date=date_start,
        end_date=date_end,
    )
    return result

@router.get("/sales/individual-condition", description="""
    **Получить данные по ИУ за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
""")
async def get_individual_condition_by_date(
        date_start: datetime.date,
        date_end: datetime.date,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    result = await service.get_sums_individual_conditions_by_period_with_category(
        start_date=date_start,
        end_date=date_end)
    return result