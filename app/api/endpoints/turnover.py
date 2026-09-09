from fastapi import APIRouter, Depends, HTTPException
from app.auth import WBTurnoverFederalDistrictViewer
from starlette import status

from app.domain.models import TurnoverByFederalDistrictData
from app.service.turnover import TurnoverService
from app.dependencies import get_turnover_service

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
        _: WBTurnoverFederalDistrictViewer = Depends(),
        service: TurnoverService = Depends(get_turnover_service),

):
    result = await service.turnover_by_federal_district()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articles data not found")
    return result
