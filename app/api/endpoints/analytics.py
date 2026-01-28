from fastapi import APIRouter
from fastapi.params import Depends


from app.dependencies import get_analytics_service
from app.domain.models import AnalyticsTimeExecutingWithWBAccount
from app.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Аналитика"])

@router.get("/warehouse/time-execution-delivery",
            response_model=list[AnalyticsTimeExecutingWithWBAccount],
            description="""
**Получить время исполнения поставки со склада на ВБ склад в статус сортировки**\n
            """
            )
async def warehouse_time_execution_delivery(
        service: AnalyticsService = Depends(get_analytics_service),
):
    """Получить время исполнения поставок для каждого аккаунта"""
    result = await service.get_warehouse_time_execution()
    return result