from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.domain.models import UnitEconomics, UserPermissions
from app.service.unit_economics import UnitEconomicsService
from app.dependencies import get_unit_economics_service, get_info_from_token

router = APIRouter(tags=['Unit Economics'])


@router.get("/unit_economics", response_model=List[UnitEconomics], description="some_data")
async def get_article_details(
        user: UserPermissions = Depends(get_info_from_token),
        service: UnitEconomicsService = Depends(get_unit_economics_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    user_details = await service.get_current_data()
    if not user_details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articles data not found")
    return user_details
