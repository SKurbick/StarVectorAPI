from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, Body
from starlette import status

from app.domain.models import TurnoverByFederalDistrictData, UserPermissions
from app.service.turnover import TurnoverService
from app.dependencies import get_turnover_service, get_info_from_token

router = APIRouter(tags=['Оборачиваемость'], prefix="/turnover")

example_turnover_by_federal_district = {
    123455677: {
        "Центральный":
            {"daily_average": 500,
             "balance_for_number_of_days": 50},
        "Северо-Кавказский":
            {"daily_average": 500,
             "balance_for_number_of_days": 50},
    },
    765432112: {
        "Центральный":
            {"daily_average": 500,
             "balance_for_number_of_days": 50},
        "Приволжский":
            {"daily_average": 500,
             "balance_for_number_of_days": 50},
    },
}


@router.get("/by_federal_district", response_model=TurnoverByFederalDistrictData, description="Оборачиваемость по округу")
async def stocks_quantity(
        user: UserPermissions = Depends(get_info_from_token),
        service: TurnoverService = Depends(get_turnover_service),

):
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    result = await service.turnover_by_federal_district()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articles data not found")
    return result
