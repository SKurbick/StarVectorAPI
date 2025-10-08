from fastapi import APIRouter, Depends, status

from app.dependencies import get_fin_reports_service
from app.domain.models import WeekleFinReportsAggregated
from app.service.fin_reports import FinReportsService


router = APIRouter(prefix="/fin_reports", tags=["Финансовые отчеты"])


@router.get("/aggregated", status_code=status.HTTP_200_OK, 
            description="Еженедельный отчет от WB по всем финансовым оперциям.")
async def get_fin_reports_agg(
    service: FinReportsService = Depends(get_fin_reports_service),
) -> list[WeekleFinReportsAggregated]:
    return await service.get_fin_reports_aggregated()
