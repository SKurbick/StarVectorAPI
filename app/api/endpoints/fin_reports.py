from typing import Optional
from datetime import date, timedelta
import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.dependencies.sales_report import get_sales_reports_service, SalesReportsService
from app.dependencies import (
    get_dates_period_filter,
    verify_scheduler_api_key,
    get_info_from_token,
)
from app.domain.models import (
    WeeklyFinReportsAggregated,
    PeriodRequestModel,
    UserPermissions,
    SalesReportFetchResponse,
)

reports_by_week_description = "1 - текущая неделя или до указанной даты. С повышением числа (2, 3 ...) будут учтены в ответе предыдущие недели"

router = APIRouter(prefix="/fin_reports", tags=["Финансовые отчеты"])


@router.get("/weekly_aggregated", status_code=status.HTTP_200_OK,
            description="Еженедельные отчеты от WB по всем финансовым оперциям")
async def get_weekly_fin_reports_agg(
    user: UserPermissions = Depends(get_info_from_token),
    service: SalesReportsService = Depends(get_sales_reports_service),
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    number_of_last_weeks: Optional[int] = Query(None, gt=0, example=1, description=reports_by_week_description),
) -> list[WeeklyFinReportsAggregated]:
    if not user.crm_viewing_unit_economics:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_sales_reports_aggregated(period, number_of_last_weeks)


@router.post("/jobs/fetch_daily_financial_reports", status_code=200, include_in_schema=True)
async def fetch_daily_fin_reports(
    _: None = Depends(verify_scheduler_api_key),
    service: SalesReportsService = Depends(get_sales_reports_service),
    date_from: date | None = None,
    date_to: date | None = None,
) -> SalesReportFetchResponse:
    """
    Загрузить ежедневные отчеты о продажах.
    """
    yesterday = date.today() - timedelta(days=1)

    try:
        result = await service.fetch_sales_reports(
            date_from=date_from or yesterday,
            date_to=date_to or yesterday,
            period="daily",
        )
        return {"message": "Data loaded successfully", "details": result}
    except Exception as e:
        logging.error(f"Исключение во время получения ежедневных отчетов: {e=}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while loading data: {e}",
        )


@router.post("/jobs/fetch_weekly_financial_reports", status_code=200, include_in_schema=True)
async def fetch_weekly_fin_reports(
    _: None = Depends(verify_scheduler_api_key),
    service: SalesReportsService = Depends(get_sales_reports_service),
    date_from: date | None = None,
    date_to: date | None = None,
) -> SalesReportFetchResponse:
    """
    Загрузить еженедельные отчеты о продажах
    """
    today = date.today()
    last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)

    try:
        result = await service.fetch_sales_reports(
            date_from=date_from or last_sunday,
            date_to=date_to or today,
            period="weekly",
        )
        return {"message": "Data loaded successfully", "details": result}
    except Exception as e:
        logging.error(f"Исключение во время получения еженедельных отчетов: {e=}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while loading data: {e}",
        )


@router.post("/jobs/update_daily_fin_reports_agg", status_code=200, include_in_schema=True)
async def update_daily_fin_reports_agg(
    number_of_last_days: int = Query(1, description="1 - за предыдущий день. 2, 3 и далее - количество последних дней"),
    service: SalesReportsService = Depends(get_sales_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
    try:
        result = await service.update_daily_fin_reports_agg(number_of_last_days)
        return {"message": "Daily financial reports_agg updated successfully", "detail": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating daily financial reports_agg: {e}",
        )


@router.post("/jobs/update_daily_fin_reports_deductions", status_code=200, include_in_schema=True)
async def update_daily_fin_reports_deductions(
    number_of_last_days: int = Query(1, description="1 - за предыдущий день. 2, 3 и далее - количество последних дней"),
    service: SalesReportsService = Depends(get_sales_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
    try:
        result = await service.update_daily_fin_reports_deduction(number_of_last_days)
        return {"message": "Daily financial reports deductions updated successfully", "detail": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating daily financial reports deductions: {e}",
        )
