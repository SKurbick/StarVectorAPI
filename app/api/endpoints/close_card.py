from fastapi import APIRouter, Body, Depends

from app.dependencies import get_close_card_service
from app.service.close_card import CloseCardService
from app.domain.models import CloseCardsRequest, CloseCardPreviewRequest, ClosePreviewResponse, CloseOperationResponse


router  = APIRouter(prefix="/closing_cards", tags=["Закрытие карточек"])


@router.post("/preview")
async def close_preview(
    data: CloseCardPreviewRequest = Body(..., description="Аккаунты c данными карточек к закрытию."),
    service: CloseCardService = Depends(get_close_card_service),
) -> ClosePreviewResponse:
    return await service.close_cards_preview(data)


@router.post("/close")
async def close_cards(
    data: CloseCardsRequest,
    service: CloseCardService = Depends(get_close_card_service),
) -> CloseOperationResponse:
    return await service.close_cards(data)
