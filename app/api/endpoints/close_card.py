from fastapi import APIRouter, Body, Query, Depends, HTTPException, status

from app.dependencies import get_close_card_service
from app.service.close_card import CloseCardService
from app.domain.models import CloseCardsRequest


router  = APIRouter(prefix="/closing_cards", tags=["Закрытие карточек"])


@router.post("/preview")
async def close_preview(
    data: CloseCardsRequest = Body(..., description="Список артикулов."),
    service: CloseCardService = Depends(get_close_card_service),
):
    return await service.close_cards_preview(data)


@router.post("/close")
async def close_cards(
    data: CloseCardsRequest,
    user_confirmation: bool = Query(False, description="Подтверждение пользователя на закрытие карточек"),
    service: CloseCardService = Depends(get_close_card_service),
):
    if not user_confirmation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Закрытие карточек не подтверждено.")

    return await service.close_cards(data)
