from fastapi import APIRouter, Depends, status, UploadFile, File

from app.dependencies import get_penalty_service, get_dates_period_filter
from app.domain.models import DaylyPenaltiesReport, PeriodRequestModel, PenaltyAnnotationUpdate, ResponseMessage
from app.service.penalties import PenaltyService
from app.domain.enums import LossOwnerEnum


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

@router.get("/loss_owners", status_code=status.HTTP_200_OK,
            description="Список доступных владельцев потерь")
async def get_all_loss_owners() -> list[dict[str, int | str]]:
    return [
        {"id": owner.id, "loss_owner": owner.value_for_db}
        for owner in LossOwnerEnum
    ]

@router.patch("/penalty_annotation_from_excel", status_code=status.HTTP_200_OK,
              description="Обновление аннотаций к штрафам с Excel файла")
async def update_penalty_annotations_from_excel(
    upload_file: UploadFile = File(...),
    service: PenaltyService = Depends(get_penalty_service)
) -> ResponseMessage:
    await service.update_penalty_annotations_from_excel(upload_file=upload_file)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated"
    )