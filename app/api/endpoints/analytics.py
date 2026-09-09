from fastapi import APIRouter
from fastapi.params import Depends

from app.auth import WBAnalyticsWHDTViewer
from app.dependencies import get_analytics_service
from app.domain.models import AnalyticsTimeExecutingWithWBAccount
from app.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get(
    "/warehouse/time-execution-delivery",
    response_model=list[AnalyticsTimeExecutingWithWBAccount],
    description="""
Получить время исполнения поставки со склада на ВБ склад в статусе сортировки.
""",
)
async def warehouse_time_execution_delivery(
    # _: WBAnalyticsWHDTViewer = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[AnalyticsTimeExecutingWithWBAccount]:
    """
    Возвращает время исполнения поставок для каждого аккаунта.
    """
    return await service.get_warehouse_time_execution()
