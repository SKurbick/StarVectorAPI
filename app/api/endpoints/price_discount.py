from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from app.domain.models import PriceDiscountResponseModel, PriceDiscountContainer, ResponseMessage
from app.dependencies import get_price_discount_service
from app.service.price_discount import PriceDiscountService

router = APIRouter(tags=["Price and Discount"])


@router.post("/price_discount", response_model=ResponseMessage)
async def update_price_discount(
        data: PriceDiscountResponseModel,
        service: PriceDiscountService = Depends(get_price_discount_service)

):
    try:
        await service.update(data=data)
        return {
            "status": 200,
            "message": "успешно ебать 👍 поздравляю"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обновления данных. Error: {e}")
