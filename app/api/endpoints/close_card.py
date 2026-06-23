from fastapi import APIRouter, Body, Depends, HTTPException

from starlette import status

from app.dependencies import get_close_card_service, get_info_from_token
from app.service.close_card import CloseCardService
from app.domain.models import (
    CloseCardsRequest,
    CloseCardPreviewRequest,
    ClosePreviewResponse,
    CloseOperationResponse,
    UserPermissions
)

router = APIRouter(prefix="/closing_cards", tags=["Закрытие карточек"])


@router.post("/preview", deprecated=True)
async def close_preview(
        data: CloseCardPreviewRequest = Body(..., description="Аккаунты c данными карточек к закрытию."),
        user: UserPermissions = Depends(get_info_from_token),
        service: CloseCardService = Depends(get_close_card_service),
) -> ClosePreviewResponse:
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.close_cards_preview(data)


@router.post("/close", deprecated=True)
async def close_cards(
        data: CloseCardsRequest,
        user: UserPermissions = Depends(get_info_from_token),
        service: CloseCardService = Depends(get_close_card_service),
) -> CloseOperationResponse:
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.close_cards(data)
