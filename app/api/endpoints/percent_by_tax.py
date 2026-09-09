from typing import List

from fastapi import APIRouter, Depends
from app.auth import WBTaxesPercentEditor

from app.dependencies import get_percent_by_tax_service
from app.service.percent_by_tax import PercentByTaxService
from app.domain.models import (
    PercentByTaxResponseModel,
    ResponseMessage,
    DefaultPercentByTaxResponseModel,
)

router = APIRouter(tags=["Упрощённая система налогооблажения"])


@router.post("/update_percent_by_tax", response_model=ResponseMessage)
async def update_percent_by_tax(
        data: List[PercentByTaxResponseModel],
        _: WBTaxesPercentEditor = Depends(),
        service: PercentByTaxService = Depends(get_percent_by_tax_service)
):
    await service.update_tax_by_article_id(data=data)
    print(*data)
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }


@router.post("/default_percent_by_tax", response_model=ResponseMessage)
async def update_default_percent_by_tax(
        data: DefaultPercentByTaxResponseModel,
        _: WBTaxesPercentEditor = Depends(),
        service: PercentByTaxService = Depends(get_percent_by_tax_service)
):
    print(data.model_dump())
    await service.update_default_percent_by_tax(data)
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }
