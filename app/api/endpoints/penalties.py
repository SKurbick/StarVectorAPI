from fastapi import APIRouter, Depends, status

from app.dependencies import get_penalty_service, get_dates_period_filter
from app.domain.models import DaylyPenaltiesReport, PeriodRequestModel, PenaltyAnnotationUpdate, ResponseMessage
from app.service.penalties import PenaltyService


router = APIRouter(prefix="/penalties", tags=["Штрафы WB"])


@router.get("/details", status_code=status.HTTP_200_OK,
            description="Штрафы по каждому дню или за период")
async def get_penalties_details(
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    service: PenaltyService = Depends(get_penalty_service),
) -> list[DaylyPenaltiesReport]:
    return await service.get_penalties_details(period)


@router.patch("/penalty_annotation", status_code=status.HTTP_200_OK,
              description="Обновление аннотаций к штрафам")
async def update_penalty_annotation(
    data: PenaltyAnnotationUpdate,
    service: PenaltyService = Depends(get_penalty_service),
) -> ResponseMessage:
    await service.update_penalty_annotation(data)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated"
    )
