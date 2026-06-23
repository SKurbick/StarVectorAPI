from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_open_card_service, get_info_from_token
from app.service.open_card import OpenCardService
from app.domain.models import OpenCardsRequest, UserPermissions

router  = APIRouter(prefix="/opening_cards", tags=["Открытие карточек"])


@router.post("/open", deprecated=True)
async def open_cards(
    data: OpenCardsRequest,
    user: UserPermissions = Depends(get_info_from_token),
    service: OpenCardService = Depends(get_open_card_service),
):
    if not user.crm_change_price_and_discounts:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.open_cards(data)
