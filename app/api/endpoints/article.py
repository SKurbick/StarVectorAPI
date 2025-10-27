from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ArticleDetails, ArticleCloseRequest, ResponseMessage
from app.service.article import ArticleService
from app.dependencies import get_article_service


router = APIRouter(tags=['Articles'])


@router.get("/article_details", response_model=List[ArticleDetails], description="some_data")
async def get_article_details(
        service: ArticleService = Depends(get_article_service)
):
    user_details = await service.get_article_details()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details


@router.post("/articles/close", status_code=status.HTTP_202_ACCEPTED,
             description="Закрыть карточку и обнулить остатки на маркетплейсе")
async def close_articles(
    data: ArticleCloseRequest,
    service: ArticleService = Depends(get_article_service)
):
    result = await service.close_articles(data)
    return ResponseMessage(
        status=status.HTTP_202_ACCEPTED,
        message="Запрос на закрытие карточки принят."
    )
