from fastapi import APIRouter, Query, Depends

from app.service.marketplace_charcs import MarketplaceCharcsService
from app.dependencies import get_marketplace_charcs_service
from app.domain.models import GetWbCharcsResponse

router = APIRouter(prefix="/charcs", tags=["Характеристики товаров маркетплейсов"])


@router.get("/wb", description="Получить характеристики предмета Wildberries")
async def get_subject_charcs_from_wb(
    subject_id: int = Query(..., example=338, description="id предмета"),
    service: MarketplaceCharcsService = Depends(get_marketplace_charcs_service),
) -> GetWbCharcsResponse:
    return await service.get_subjects_charcs_from_wb(subject_id)
