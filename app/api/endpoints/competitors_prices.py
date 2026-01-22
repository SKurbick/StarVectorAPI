from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_competitor_price_service, get_info_from_token
from app.domain.models import CompetitorPriceResponse, UserPermissions
from app.service.competitors_prices import CompetitorPriceService

router = APIRouter(tags=["Цены конкурентов"])


@router.get("/competitors-prices", status_code=status.HTTP_200_OK,
            description="Цены конкурентов")
async def get_all_competitor_prices(
        user: UserPermissions = Depends(get_info_from_token),
        service: CompetitorPriceService = Depends(get_competitor_price_service),
) -> list[CompetitorPriceResponse]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_all_competitor_prices()
