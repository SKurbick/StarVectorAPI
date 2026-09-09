from fastapi import APIRouter, Depends, HTTPException
from app.auth import WBStocksQuantityEditor, WBStocksQuantityViewer
from starlette import status

from app.dependencies import get_stocks_quantity_service, validate_edit_quantity_data
from app.domain.models import (
    StocksQuantity,
    EditQuantityValidationResult,
    StocksEditResponse,
)
from app.service.stocks_quantity import StocksQuantityService


router = APIRouter(tags=['Состояние по остаткам'], prefix="/stock")


@router.get("/quantity", response_model=list[StocksQuantity], description="Состояние остатков")
async def stocks_quantity(
        _: WBStocksQuantityViewer = Depends(),
        service: StocksQuantityService = Depends(get_stocks_quantity_service)
):
    user_details = await service.get_all_data()
    if not user_details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articles data not found")
    return user_details


# TODO: вынести в другой сервис
@router.post(
    "/edit_quantity",
    response_model=StocksEditResponse,
    description="Изменение виртуальных остатков. Метод работает асинхронно, успешно отправленные остатки обновляются в течение 5 минут."
)
async def edit_stocks_quantity(
        _: WBStocksQuantityEditor = Depends(),
        validation: EditQuantityValidationResult = Depends(validate_edit_quantity_data),
        service: StocksQuantityService = Depends(get_stocks_quantity_service),
):
    result = None

    if validation.allowed:
        result = await service.edit_stocks_quantity(validation.allowed)

    details = {
        "result": result
    }

    if validation.invalid:
        details["not_found"] = {
            "data": validation.invalid,
            "message": "Нет данных по переданным баркодам." if validation.invalid else None
        }

    if validation.closed_with_nonzero:
        details["closed_with_nonzero"] = {
            "data": validation.closed_with_nonzero,
            "message": (
                "Некоторые карточки закрыты. Чтобы изменить остатки (кроме 0), "
                "сначала откройте их. Для обнуления - установите amount=0."
            )
        }

    return {
        "status": status.HTTP_200_OK,
        "message": "Запрос обработан",
        "details": details
    }
