from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_percent_by_tax_service, get_info_from_token
from app.service.percent_by_tax import PercentByTaxService
from app.domain.models import (
    PercentByTaxResponseModel,
    ResponseMessage,
    DefaultPercentByTaxResponseModel,
    UserPermissions
)

router = APIRouter(tags=["Упрощённая система налогооблажения"])


@router.post("/update_percent_by_tax", response_model=ResponseMessage)
async def update_percent_by_tax(
        data: List[PercentByTaxResponseModel],
        user: UserPermissions = Depends(get_info_from_token),
        service: PercentByTaxService = Depends(get_percent_by_tax_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    await service.update_tax_by_article_id(data=data)
    print(*data)
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }


@router.post("/default_percent_by_tax", response_model=ResponseMessage)
async def update_default_percent_by_tax(
        data: DefaultPercentByTaxResponseModel,
        user: UserPermissions = Depends(get_info_from_token),
        service: PercentByTaxService = Depends(get_percent_by_tax_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    print(data.model_dump())
    await service.update_default_percent_by_tax(data)
    return {
        "status": 200,
        "message": "успешно ебать 👍 поздравляю"
    }
