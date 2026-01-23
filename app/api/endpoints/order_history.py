from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status

from app.dependencies import get_info_from_token
from app.dependencies.order_history import get_order_history_service
from app.domain.models import OrderHistoryResponseModel, UserPermissions
from app.service.order_history import OrderHistoryService


router = APIRouter(tags=["Orders History"])


@router.get("/orders_history", status_code=200, response_model=list[OrderHistoryResponseModel])
async def get_orders_history(
    product_id: str = Query(...),
    start: date | None = Query(None),
    end: date | None = Query(None),
    user: UserPermissions = Depends(get_info_from_token),
    service: OrderHistoryService = Depends(get_order_history_service)
) -> list[OrderHistoryResponseModel]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_orders_history(product_id, start, end)