from typing import List

from fastapi import APIRouter, Depends, HTTPException
from app.domain.models import UnitEconomics
from app.service.unit_economics import UnitEconomicsService
from app.dependencies import get_unit_economics_service

router = APIRouter(tags=['Unit Economics'])


@router.get("/unit_economics", response_model=List[UnitEconomics], description="some_data")
async def get_article_details(
        service: UnitEconomicsService = Depends(get_unit_economics_service)
):
    user_details = await service.get_current_data()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details
