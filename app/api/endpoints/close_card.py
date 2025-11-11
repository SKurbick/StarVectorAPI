from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.dependencies import get_close_card_service
from app.service.close_card import CloseCardService
from app.domain.models import CloseCardsRequest, CardDataByAccountRequest


router  = APIRouter(prefix="/closing_cards", tags=["Закрытие карточек"])


@router.post("/preview")
async def close_preview(
    data: CardDataByAccountRequest = Body(..., description="Аккаунты c данными карточек к закрытию."),
    service: CloseCardService = Depends(get_close_card_service),
):
    return await service.close_cards_preview(data)


@router.post("/close")
async def close_cards(
    data: CloseCardsRequest = Body(..., description="Аккаунты c данными карточек к закрытию."),
    service: CloseCardService = Depends(get_close_card_service),
):
    if not data.user_confirmation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Закрытие карточек не подтверждено. user_confirmation: false")

    return await service.close_cards(data)
