from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, status, Query

from app.dependencies import get_fin_reports_service, get_dates_period_filter
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


@router.post("/jobs/fetch_daily_financial_reports")
async def fetch_daily_fin_reports(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    service: FinReportsService = Depends(get_fin_reports_service)
):
    if date_from:
        date_from = date_from.isoformat()
    
    if date_to:
        date_to = date_to.isoformat()
    
    await service.fetch_daily_fin_reports(date_from, date_to)
    return {"status": 200, "message": "so-good!"}
