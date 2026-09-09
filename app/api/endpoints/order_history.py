from datetime import date

from fastapi import APIRouter, Depends, Query
from app.auth import WBOrderHistoryViewer

from app.dependencies.order_history import get_order_history_service
from app.domain.models import OrderHistoryResponseModel
from app.service.order_history import OrderHistoryService


router = APIRouter(tags=["Orders History"])


@router.get("/orders_history", status_code=200, response_model=list[OrderHistoryResponseModel])
async def get_orders_history(
    _: WBOrderHistoryViewer = Depends(),
    product_id: str = Query(...),
    start: date | None = Query(None),
    end: date | None = Query(None),
    service: OrderHistoryService = Depends(get_order_history_service)
) -> list[OrderHistoryResponseModel]:
    return await service.get_orders_history(product_id, start, end)
