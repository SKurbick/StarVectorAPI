from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_stocks_quantity_service, validate_edit_quantity_data
from app.domain.models import StocksQuantity, ResponseMessageDetails, EditQuantityValidationResult
from app.service.stocks_quantity import StocksQuantityService


router = APIRouter(tags=['Состояние по остаткам'], prefix="/stock")


@router.get("/quantity", response_model=List[StocksQuantity], description="Состояние остатков")
async def stocks_quantity(
        service: StocksQuantityService = Depends(get_stocks_quantity_service)
):
    user_details = await service.get_all_data()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details


@router.post("/edit_quantity", response_model=ResponseMessageDetails, description="Изменение виртуальных остатков")
async def edit_stocks_quantity(
        validation: EditQuantityValidationResult = Depends(validate_edit_quantity_data),
        service: StocksQuantityService = Depends(get_stocks_quantity_service),
):
    allowed = validation.allowed
    forbidden = validation.forbidden

    if allowed:
        # await service.edit_stocks_quantity(allowed)  # метод работает но замокан для тестирования
        print(allowed)

    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю",
        "details": {
            "forbidden": forbidden
        }
    }
