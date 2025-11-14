from fastapi import APIRouter, Depends

from app.dependencies import get_open_card_service
from app.service.open_card import OpenCardService
from app.domain.models import OpenCardsRequest


router  = APIRouter(prefix="/opening_cards", tags=["Открытие карточек"])


@router.post("/open")
async def open_cards(
    data: OpenCardsRequest,
    service: OpenCardService = Depends(get_open_card_service),
):
    return await service.open_cards(data)
