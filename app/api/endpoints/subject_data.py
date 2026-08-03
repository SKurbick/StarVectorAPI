from fastapi import APIRouter, Depends, HTTPException
from starlette import status

# from app.dependencies import get_subject_data_service, get_info_from_token
# from app.service.subject_data import SubjectDataService
# from app.domain.models import CategoriesResponse, UserPermissions

router = APIRouter(prefix="/subjects", tags=["Предметы маркетплейсов"])


# @router.get("/wildberries", description="Получить предметы Wildberries по категориям", deprecated=True)
# async def get_subjects_from_wb(
#     user: UserPermissions = Depends(get_info_from_token),
#     service: SubjectDataService = Depends(get_subject_data_service)
# ) -> CategoriesResponse:
#     if not user.viewing:
#         raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
#     try:
#         return await service.get_subject_data_from_wb()
#     except Exception as e:
#         return HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Ошибка во время получения предметов Wildberries: {e}"
#         )
