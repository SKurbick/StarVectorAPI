from fastapi import APIRouter, Depends, File, UploadFile
from starlette import status

from app.auth import WBPenaltiesViewer, WBPenaltiesAnnotationsEditor
from app.dependencies import get_dates_period_filter, get_penalty_service
from app.domain.enums import LossOwnerEnum
from app.domain.models import (
    DaylyPenaltiesReport,
    PenaltyAnnotationUpdate,
    PeriodRequestModel,
    ResponseMessage,
)
from app.service.penalties import PenaltyService

router = APIRouter(prefix="/penalties", tags=["Штрафы WB"])


@router.get(
    "/details",
    status_code=status.HTTP_200_OK,
    description="Штрафы по каждому дню или за период",
)
async def get_penalties_details(
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    # _: WBPenaltiesViewer = Depends(),
    service: PenaltyService = Depends(get_penalty_service),
) -> list[DaylyPenaltiesReport]:
    """
    Возвращает штрафы за выбранный период.
    """
    return await service.get_penalties_details(period)


@router.patch(
    "/penalty_annotation",
    status_code=status.HTTP_200_OK,
    description="Обновление аннотаций к штрафам",
)
async def update_penalty_annotation(
    data: PenaltyAnnotationUpdate,
    # _: WBPenaltiesAnnotationsEditor = Depends(),
    service: PenaltyService = Depends(get_penalty_service),
) -> ResponseMessage:
    """
    Обновляет аннотации к штрафам.
    """
    await service.update_penalty_annotation(data)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated",
    )


@router.get(
    "/loss_owners",
    status_code=status.HTTP_200_OK,
    description="Список доступных владельцев потерь",
)
async def get_all_loss_owners(
    # _: WBPenaltiesViewer = Depends(),
) -> list[dict[str, int | str]]:
    """
    Возвращает справочник владельцев потерь.
    """
    return [
        {"id": owner.id, "loss_owner": owner.value_for_db}
        for owner in LossOwnerEnum
    ]


@router.put(
    "/penalty_annotation_from_excel",
    status_code=status.HTTP_200_OK,
    description="Обновление аннотаций к штрафам из Excel-файла",
)
async def update_penalty_annotations_from_excel(
    upload_file: UploadFile = File(...),
    # _: WBPenaltiesAnnotationsEditor = Depends(),
    service: PenaltyService = Depends(get_penalty_service),
) -> ResponseMessage:
    """
    Загружает аннотации к штрафам из Excel-файла.
    """
    await service.update_penalty_annotations_from_excel(upload_file=upload_file)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated",
    )
