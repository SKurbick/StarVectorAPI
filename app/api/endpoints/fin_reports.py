from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, status, Query, HTTPException

from app.dependencies import get_fin_reports_service, get_dates_period_filter, verify_scheduler_api_key
from app.domain.models import WeeklyFinReportsAggregated, PeriodRequestModel
from app.service.fin_reports import FinReportsService


reports_by_week_description = "1 - текущая неделя или до указанной даты. С повышением числа (2, 3 ...) будут учтены в ответе предыдущие недели"

router = APIRouter(prefix="/fin_reports", tags=["Финансовые отчеты"])


@router.get("/weekly_aggregated", status_code=status.HTTP_200_OK,
            description="Еженедельные отчеты от WB по всем финансовым оперциям")
async def get_weekly_fin_reports_agg(
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    number_of_last_weeks: Optional[int] = Query(None, gt=0, example=1, description=reports_by_week_description),
    service: FinReportsService = Depends(get_fin_reports_service),
) -> list[WeeklyFinReportsAggregated]:
    return await service.get_fin_reports_aggregated(period, number_of_last_weeks)


@router.post("/jobs/fetch_daily_financial_reports", status_code=200, include_in_schema=True)
async def fetch_daily_fin_reports(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    service: FinReportsService = Depends(get_fin_reports_service),
    _: None = Depends(verify_scheduler_api_key)
):
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
    service: FinReportsService = Depends(get_fin_reports_service),
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
