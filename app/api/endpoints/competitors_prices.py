from fastapi import APIRouter, Depends, status

from app.dependencies import get_competitor_price_service
from app.domain.models import CompetitorPriceResponse
from app.service.competitors_prices import CompetitorPriceService


router = APIRouter(tags=["Цены конкурентов"])


@router.get("/competitors-prices", status_code=status.HTTP_200_OK,
            description="Цены конкурентов")
async def get_all_competitor_prices(
    service: CompetitorPriceService = Depends(get_competitor_price_service),
) -> list[CompetitorPriceResponse]:
    return await service.get_all_competitor_prices()
