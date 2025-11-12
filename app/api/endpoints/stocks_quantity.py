from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_stocks_quantity_service, validate_edit_quantity_data
from app.domain.models import StocksQuantity, ResponseMessageDetails, EditQuantityValidationResult
from app.service.stocks_quantity import StocksQuantityService


router = APIRouter(tags=['Состояние по остаткам'], prefix="/stock")


@router.get("/quantity", response_model=list[StocksQuantity], description="Состояние остатков")
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
    if validation.allowed:
        await service.edit_stocks_quantity(validation.allowed)

    details = {"invalid": validation.invalid}

    if validation.closed_with_nonzero:
        details["closed_with_nonzero"] = validation.closed_with_nonzero
        details["message"] = (
            "Некоторые карточки закрыты. Чтобы изменить остатки (кроме 0), "
            "сначала откройте их. Для обнуления - установите amount=0."
        )

    return {
        "status": 200,
        "message": "Запрос обработан",
        "details": details
    }
