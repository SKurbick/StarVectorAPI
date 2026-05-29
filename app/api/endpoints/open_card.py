from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_info_from_token
from app.domain.models import UserPermissions
from app.infrastructure.marketplace_card_manager.schemas import OpenCardsRequest
from app.dependencies.marketplace_cards import MarketplaceCardsService, get_mcm_service

router  = APIRouter(prefix="/opening_cards", tags=["Открытие карточек"])


@router.post("/open")
async def open_cards(
    data: OpenCardsRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: MarketplaceCardsService = Depends(get_mcm_service),
):
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.open_cards(data)
