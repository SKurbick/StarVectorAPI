from fastapi import APIRouter, Depends

from app.domain.models import ICNetProfitResponseModel
from app.dependencies.ic_net_profit import get_ic_net_profit_service
from app.service.ic_net_profit_service import ICNetProfitService

router = APIRouter(tags=["IC Net Profit"])

@router.get("/ic_net_profit", status_code=200, response_model=list[ICNetProfitResponseModel])
async def get_ic_net_profit(
        service: ICNetProfitService = Depends(get_ic_net_profit_service)
) -> list[ICNetProfitResponseModel]:
    return await service.get_net_profit()