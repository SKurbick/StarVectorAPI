from fastapi import APIRouter, Depends, status

from app.service.competitors import CompetitorsService
from app.dependencies.competitors import get_competitors_service
from app.domain.models import CompetitorResponseModel


router = APIRouter(tags=["Competitors"])

@router.get("/competitors", status_code=status.HTTP_200_OK,response_model=list[CompetitorResponseModel])
async def get_competitors(service: CompetitorsService = Depends(get_competitors_service)) -> list[CompetitorResponseModel]:
    return await service.get_competitors()