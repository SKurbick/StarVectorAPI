from typing import List

from fastapi import APIRouter, Depends
from app.domain import CardData
from app.service import CardDataService
from app.dependencies import get_card_data_service

router = APIRouter(tags=["Card INFO"])


@router.get("/card_data/{article_id}", response_model=CardData)
async def card_data_by_article_id(
        article_id: int,
        service: CardDataService = Depends(get_card_data_service)
):
    return await service.get_card_data_by_article_id(article_id)


@router.get("/all_card_data", response_model=List[CardData])
async def all_card_data(
        service: CardDataService = Depends(get_card_data_service)
):
    return await service.get_all_card_data()
