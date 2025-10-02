from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, HTTPException

from app.dependencies.product import get_product_service
from app.domain.models import ResponseMessage, CreateProduct, ProductResponse, SubjectDataWithProductsResponse
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


@router.get("/{product_id}", status_code=status.HTTP_200_OK)
async def get_product(
    product_id: str,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await service.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product data not found")

    return product


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_product(
    data: CreateProduct,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await service.create_product(data)

    return product


@router.put("/{product_id}", status_code=status.HTTP_200_OK)
async def update_product(
    product_id: str,
    data: CreateProduct,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await service.update_product(
        product_id=product_id,
        data=data,
    )

    return product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: str,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ResponseMessage:
    await service.delete(product_id)

    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Product was deleted",
    )
