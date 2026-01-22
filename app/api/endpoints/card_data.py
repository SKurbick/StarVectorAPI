from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.domain import CardData
from app.domain.models import UserPermissions
from app.service import CardDataService
from app.dependencies import get_card_data_service, get_info_from_token

router = APIRouter(tags=["Card INFO"])


@router.get("/card_data/{article_id}", response_model=CardData)
async def card_data_by_article_id(
        article_id: int,
        user: UserPermissions = Depends(get_info_from_token),
        service: CardDataService = Depends(get_card_data_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_card_data_by_article_id(article_id)


@router.get("/all_card_data", response_model=List[CardData])
async def all_card_data(
        user: UserPermissions = Depends(get_info_from_token),
        service: CardDataService = Depends(get_card_data_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_all_card_data()
