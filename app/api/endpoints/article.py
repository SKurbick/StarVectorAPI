from typing import List

from fastapi import APIRouter, Depends, HTTPException
from app.domain.models import ArticleDetails
from app.service.article import ArticleService
from app.dependencies import get_article_service

router = APIRouter(tags=['Articles'])


@router.get("/article_details", response_model=List[ArticleDetails], description="somed")
async def get_article_details(
        service: ArticleService = Depends(get_article_service)
):
    user_details = await service.get_article_details()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details
