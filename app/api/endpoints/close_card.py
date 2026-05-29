from fastapi import APIRouter, Body, Depends, HTTPException

from starlette import status

from app.dependencies import get_info_from_token
from app.domain.models import UserPermissions
from app.dependencies.marketplace_cards import get_mcm_service, MarketplaceCardsService
from app.infrastructure.marketplace_card_manager.schemas import (
    CloseCardPreviewRequest,
    CloseCardsRequest,
    ClosePreviewResponse,
    CloseOperationResponse,
)

router = APIRouter(prefix="/closing_cards", tags=["Закрытие карточек"])


@router.post("/preview")
async def close_preview(
        data: CloseCardPreviewRequest = Body(..., description="Аккаунты c данными карточек к закрытию."),
        user: UserPermissions = Depends(get_info_from_token),
        service: MarketplaceCardsService = Depends(get_mcm_service),
) -> ClosePreviewResponse:
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.close_cards_preview(data)


@router.post("/close")
async def close_cards(
        data: CloseCardsRequest,
        user: UserPermissions = Depends(get_info_from_token),
        service: MarketplaceCardsService = Depends(get_mcm_service),
) -> CloseOperationResponse:
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.close_cards(data)
