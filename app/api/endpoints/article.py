from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.domain.models import ArticleDetails, UserPermissions
from app.service.article import ArticleService
from app.dependencies import get_article_service, get_info_from_token

router = APIRouter(tags=['Articles'])


@router.get("/article_details", response_model=List[ArticleDetails], description="some_data")
async def get_article_details(
        user: UserPermissions = Depends(get_info_from_token),
        service: ArticleService = Depends(get_article_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    user_details = await service.get_article_details()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details
