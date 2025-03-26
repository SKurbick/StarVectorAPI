from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, Body
from app.domain.models import StocksQuantity, ResponseMessage, UpdateStocksQuantityResponseModel
from app.service.stocks_quantity import StocksQuantityService
from app.dependencies import get_stocks_quantity_service

router = APIRouter(tags=['Состояние по остаткам'], prefix="/stock")

example_edit_quantity = {
    "ХАЧАТРЯН": {"stocks": [{"amount": 748, "sku": "2040464284361"}, {"amount": 42, "sku": "2040464284385"}]},
    "ПИЛОСЯН": {"stocks": [{"amount": 8534, "sku": "2037786392119"}]}
}


@router.get("/quantity", response_model=List[StocksQuantity], description="Состояние остатков")
async def stocks_quantity(
        service: StocksQuantityService = Depends(get_stocks_quantity_service)
):
    user_details = await service.get_all_data()
    if not user_details:
        raise HTTPException(status_code=404, detail="Articles data not found")
    return user_details


@router.post("/edit_quantity", response_model=ResponseMessage, description="Изменение виртуальных остатков")
async def edit_stocks_quantity(
        edit_data: Dict[str, UpdateStocksQuantityResponseModel] = Body(example=example_edit_quantity),
        service: StocksQuantityService = Depends(get_stocks_quantity_service),

):
    # await service.edit_stocks_quantity(edit_data) # метод работает но замокан для тестирования
    print(edit_data)
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }
