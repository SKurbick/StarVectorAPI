from datetime import datetime
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from starlette import status

from app.dependencies import get_info_from_token
from app.dependencies import get_product_service
from app.domain.models import (
    SubjectDataWithProductsResponse,
    UserPermissions,
    ProductWBCards,
    ProductWBSpecificationResponse,
    ProsuctWBSpecificationUpdate,
    ProductUpdateSpecificationsResponse,
    CardOperationResponse
)
from app.service.product import ProductService


router = APIRouter(prefix="/products", tags=["Товары"])


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
        id: str = Path(..., description="Локальный артикул товара."),
        user: UserPermissions = Depends(get_info_from_token),
        service: ProductService = Depends(get_product_service),
) -> ProductWBCards:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_poduct_cards(product_id=id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get("/{id}/wb/specifications", status_code=status.HTTP_200_OK, description="""
    **Получить спецификации товара.**
    id: локальный артикул товара (wild).
""")
async def get_product_wb_specifications(
    id: str = Path(..., description="Локальный артикул товара."),
    user: UserPermissions = Depends(get_info_from_token),
    service: ProductService = Depends(get_product_service),
) -> ProductWBSpecificationResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    try:
        return await service.get_product_wb_specifications(id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
        "/wb/specifications/update", 
        status_code=status.HTTP_200_OK,
        description="**Обновить спецификации товара.**"
)
async def update_product_wb_specifications(
    data: ProsuctWBSpecificationUpdate,
    user: UserPermissions = Depends(get_info_from_token),
) -> ProductUpdateSpecificationsResponse:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")

    task_id = f"create_{uuid.uuid4().hex}"
    return ProductUpdateSpecificationsResponse(
        message="Запрос на обновление спецификаций товара принят в обработку",
        product_id=data.id,
        cards_for_update=[CardOperationResponse(
            task_id=task_id,
            status="queued",
            message="Запрос на создание карточки принят в обработку",
            account="Вектор",
            product_id=data.id,
            nm_id=None,
            created_at=datetime.now()
        )]
    )
