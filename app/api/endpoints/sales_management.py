from typing import Optional
import datetime
from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from app.dependencies.sales_management import get_sales_management_service
from app.domain.models import SalesManagementBaseSummWithDate
from app.service.sales_management import SalesManagementService

router = APIRouter(prefix="/sales-management", tags=["Управление продажами"])


@router.get("/sales/revenue/{date}", response_model=list[SalesManagementBaseSummWithDate], description="""
    **Получить выручку по категориям за конкретный день**\n
    date: format date, example: 2025-12-18,
    good_category: Optinal row, example 'Казаны' 
""")
async def get_revenue_by_date(
        date: datetime.date,
        good_category: Optional[str] = None,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    return await service.get_sum_sales_category_by_date(date, good_category)


@router.get("/sales/revenue", description="""
    **Получить выручку по категориям за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
""")
async def get_revenue_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    if date_start == date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="error period")
    result = await service.get_sum_revenue_category_by_period_with_managers(
        start_date=date_start,
        end_date=date_end,
    )
    return result


@router.get("/sales/ic", description="""
    **Получить данные по ИУ за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18
""")
async def get_individual_condition_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    if date_start == date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="error period")
    result = await service.get_sums_individual_conditions_by_period_with_category(
        start_date=date_start,
        end_date=date_end)
    return result


@router.get("/sales/browsing", description="""    
    **Получить данные по статистики просмторов\кликов категорий за период**\n
    date_start: format date, example: 2025-12-25
    date_end: format date, example: 2025-12-18""")
async def get_browsing_by_period(
        date_start: datetime.date,
        date_end: datetime.date,
        service: SalesManagementService = Depends(get_sales_management_service)
):
    if date_start < date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="reverse date")
    if date_start == date_end:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="error period")
    result = await service.get_browsing_info_by_category_and_period(
        start_date=date_start,
        end_date=date_end)
    return result
