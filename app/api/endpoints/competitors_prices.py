from fastapi import APIRouter, Depends, status

from app.dependencies import get_competitors_prices_service
from app.service.competitors_prices import CompetitorsPricesService


router = APIRouter(prefix="/competitors", tags=["Цены конкурентов"])


@router.get("/prices", status_code=status.HTTP_200_OK,
            description="Цены конкурентов")
async def get_competitors_prices(
    service: CompetitorsPricesService = Depends(get_competitors_prices_service),
):
    await service.get_competitors_prices()
    return {"message": "So good!"}
