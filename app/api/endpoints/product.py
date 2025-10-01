from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.product import get_product_service
from app.domain.models import SubjectDataWithProductsResponse
from app.service.product import ProductService


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/grouped_by_subjects")
async def get_products_grouped_by_subjects(
    service: Annotated[ProductService, Depends(get_product_service)],
    limit: Annotated[int, Query(ge=1)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SubjectDataWithProductsResponse]:
    return await service.get_products_grouped_by_subjects(
        limit=limit,
        offset=offset,
    )
