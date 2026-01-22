from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.dependencies import get_info_from_token
from app.domain.models import ICNetProfitResponseModel, UserPermissions
from app.dependencies.ic_net_profit import get_ic_net_profit_service
from app.service.ic_net_profit_service import ICNetProfitService

router = APIRouter(tags=["IC Net Profit"])

@router.get("/ic_net_profit", status_code=200, response_model=list[ICNetProfitResponseModel])
async def get_ic_net_profit(
        user: UserPermissions = Depends(get_info_from_token),
        service: ICNetProfitService = Depends(get_ic_net_profit_service)
) -> list[ICNetProfitResponseModel]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_net_profit()