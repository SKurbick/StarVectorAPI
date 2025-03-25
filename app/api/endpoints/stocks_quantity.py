from typing import List

from fastapi import APIRouter, Depends, HTTPException
from app.domain.models import StocksQuantity
from app.service.stocks_quantity import StocksQuantityService
from app.dependencies import get_stocks_quantity_service

router = APIRouter(tags=['Состояние по остаткам'])


@router.get("/get_stocks_quantity", response_model=List[StocksQuantity], description="some_data")
async def get_article_details(
        service: StocksQuantityService = Depends(get_stocks_quantity_service)
):
    user_details = await service.get_all_data()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details
