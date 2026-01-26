from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.dependencies import get_info_from_token
from app.dependencies.product import get_product_service
from app.domain.models import SubjectDataWithProductsResponse, UserPermissions
from app.service.product import ProductService


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/grouped_by_subjects", status_code=status.HTTP_200_OK)
async def get_products_grouped_by_subjects(
    service: Annotated[ProductService, Depends(get_product_service)],
    limit: Annotated[int, Query(ge=1)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: UserPermissions = Depends(get_info_from_token),
) -> list[SubjectDataWithProductsResponse]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_products_grouped_by_subjects(
        limit=limit,
        offset=offset,
    )
