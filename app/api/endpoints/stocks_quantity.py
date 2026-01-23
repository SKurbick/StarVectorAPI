from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_stocks_quantity_service, validate_edit_quantity_data, get_info_from_token
from app.domain.models import (
    StocksQuantity,
    ResponseMessageDetails,
    EditQuantityValidationResult,
    StocksEditResponse,
    UserPermissions
)
from app.service.stocks_quantity import StocksQuantityService


router = APIRouter(tags=['Состояние по остаткам'], prefix="/stock")


@router.get("/quantity", response_model=list[StocksQuantity], description="Состояние остатков")
async def stocks_quantity(
        user: UserPermissions = Depends(get_info_from_token),
        service: StocksQuantityService = Depends(get_stocks_quantity_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    user_details = await service.get_all_data()
    if not user_details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articles data not found")
    return user_details


@router.post(
    "/edit_quantity",
    response_model=StocksEditResponse,
    description="Изменение виртуальных остатков. Метод работает асинхронно, успешно отправленные остатки обновляются в течение 5 минут."
)
async def edit_stocks_quantity(
        user: UserPermissions = Depends(get_info_from_token),
        validation: EditQuantityValidationResult = Depends(validate_edit_quantity_data),
        service: StocksQuantityService = Depends(get_stocks_quantity_service),
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
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
