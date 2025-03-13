import datetime
from typing import List

from fastapi import APIRouter, Depends
from app.domain import NetProfitResponseModel
from app.domain.models import PeriodRequestModel
from app.service import NetProfitService
from app.dependencies import get_net_profit_service

router = APIRouter(tags=["Чистая прибыль"])


@router.post("/net_profit", response_model=List[NetProfitResponseModel])
async def get_net_profit_by_period(
        period: PeriodRequestModel,
        service: NetProfitService = Depends(get_net_profit_service)
):
    return await service.get_net_profit_by_period(period)
