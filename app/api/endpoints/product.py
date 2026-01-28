from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from starlette import status

from app.dependencies import get_info_from_token
from app.dependencies.product import get_product_service
from app.domain.models import SubjectDataWithProductsResponse, UserPermissions, ProductCard
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


@router.get("/{id}/cards", status_code=status.HTTP_200_OK, description="""
    **Получить все карточки товара**\n   
    id: локальный артикул товара (wild).
""")
async def get_product_cards(
        service: ProductService = Depends(get_product_service),
        id: str = Path(..., description="Локальный артикул товара."),
        user: UserPermissions = Depends(get_info_from_token),
) -> list[ProductCard]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_poduct_cards(product_id=id)
