from typing import List

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.domain import NetProfitResponseModel
from app.domain.models import PeriodRequestModel, UserPermissions
from app.service import NetProfitService
from app.dependencies import get_net_profit_service, get_info_from_token

router = APIRouter(tags=["Чистая прибыль"])


@router.post("/net_profit", response_model=List[NetProfitResponseModel])
async def get_net_profit_by_period(
        period: PeriodRequestModel,
        user: UserPermissions = Depends(get_info_from_token),
        service: NetProfitService = Depends(get_net_profit_service)
):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_net_profit_by_period(period)
