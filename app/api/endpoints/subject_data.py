from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_subject_data_service
from app.service.subject_data import SubjectDataService
from app.domain.models import CategoriesResponse


router = APIRouter(prefix="/subjects", tags=["Предметы маркетплейсов"])


@router.get("/wildberries", description="Получить предметы Wildberries по категориям")
async def get_subjects_from_wb(
    service: SubjectDataService = Depends(get_subject_data_service)
) -> CategoriesResponse:
    try:
        return await service.get_subject_data_from_wb()
    except Exception as e:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка во время получения предметов Wildberries: {e}"
        )
