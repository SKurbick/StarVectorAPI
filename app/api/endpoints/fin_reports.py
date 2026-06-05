from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.dependencies import (
    get_fin_reports_service,
    get_dates_period_filter,
    verify_scheduler_api_key,
    get_info_from_token
)
from app.domain.models import WeeklyFinReportsAggregated, PeriodRequestModel, UserPermissions
from app.service.fin_reports import FinReportsService


reports_by_week_description = "1 - текущая неделя или до указанной даты. С повышением числа (2, 3 ...) будут учтены в ответе предыдущие недели"

router = APIRouter(prefix="/fin_reports", tags=["Финансовые отчеты"])


@router.get("/weekly_aggregated", status_code=status.HTTP_200_OK,
            description="Еженедельные отчеты от WB по всем финансовым оперциям")
async def get_weekly_fin_reports_agg(
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    number_of_last_weeks: Optional[int] = Query(None, gt=0, example=1, description=reports_by_week_description),
    user: UserPermissions = Depends(get_info_from_token),
    service: FinReportsService = Depends(get_fin_reports_service),
) -> list[WeeklyFinReportsAggregated]:
    if not user.crm_viewing_unit_economics:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_fin_reports_aggregated(period, number_of_last_weeks)


@router.post("/jobs/fetch_daily_financial_reports", status_code=200, include_in_schema=True)
async def fetch_daily_fin_reports(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    # user: UserPermissions = Depends(get_info_from_token),
    service: FinReportsService = Depends(get_fin_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    if date_from:
        date_from = date_from.isoformat()

    if date_to:
        date_to = date_to.isoformat()

    try:
        result = await service.fetch_daily_fin_reports(date_from, date_to)
        return {"message": "Data loaded successfully", "detail": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while loading data: {e}",
        )


@router.post("/jobs/update_daily_fin_reports_agg", status_code=200, include_in_schema=True)
async def update_daily_fin_reports_agg(
    number_of_last_days: int = Query(1, description="1 - за предыдущий день. 2, 3 и далее - количество последних дней"),
    # user: UserPermissions = Depends(get_info_from_token),
    service: FinReportsService = Depends(get_fin_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
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
    # user: UserPermissions = Depends(get_info_from_token),
    service: FinReportsService = Depends(get_fin_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
    # if not user.viewing:
    #     raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        result = await service.update_daily_fin_reports_deduction(number_of_last_days)
        return {"message": "Daily financial reports deductions updated successfully", "detail": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating daily financial reports deductions: {e}",
        )

from app.infrastructure.API.wildberries.finance.wb_sales_reports import SalesReportsWBAPI
from fastapi import Request
from app.service.fin_reports import SalesReportsService, SalesReportRepository


@router.get("/test-daily-finn-list")
async def test_dayly_fin_reports_endpoint(
        request: Request,
        date_from: date | None = None,
        date_to: date | None = None,
):
    session = request.app.state.wb_session
    pool = request.app.state.pool
    repo = SalesReportRepository(pool=pool)
    service = SalesReportsService(
        session=session,
        sales_report_repo=repo,
    )

    result = await service.fetch_sales_reports(
        date_from=date_from,
        date_to=date_to,
        period="daily"
    )
    return result


@router.get("/test-weekly-finn-list")
async def test_weekly_fin_reports_endpoint(
        request: Request,
        date_from: date | None = None,
        date_to: date | None = None,
):
    session = request.app.state.wb_session
    pool = request.app.state.pool
    repo = SalesReportRepository(pool=pool)
    service = SalesReportsService(
        session=session,
        sales_report_repo=repo,
    )

    result = await service.fetch_sales_reports(
        date_from=date_from,
        date_to=date_to,
        period="weekly"
    )
    return result
