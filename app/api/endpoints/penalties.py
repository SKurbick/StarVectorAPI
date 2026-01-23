from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from starlette import status

from app.dependencies import get_penalty_service, get_dates_period_filter, get_info_from_token
from app.service.penalties import PenaltyService
from app.domain.enums import LossOwnerEnum
from app.domain.models import (
    DaylyPenaltiesReport,
    PeriodRequestModel,
    PenaltyAnnotationUpdate,
    ResponseMessage,
    UserPermissions
)


router = APIRouter(prefix="/penalties", tags=["Штрафы WB"])


@router.get("/details", status_code=status.HTTP_200_OK,
            description="Штрафы по каждому дню или за период")
async def get_penalties_details(
    period: PeriodRequestModel = Depends(get_dates_period_filter),
    user: UserPermissions = Depends(get_info_from_token),
    service: PenaltyService = Depends(get_penalty_service),
) -> list[DaylyPenaltiesReport]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return await service.get_penalties_details(period)


@router.patch("/penalty_annotation", status_code=status.HTTP_200_OK,
              description="Обновление аннотаций к штрафам")
async def update_penalty_annotation(
    data: PenaltyAnnotationUpdate,
    user: UserPermissions = Depends(get_info_from_token),
    service: PenaltyService = Depends(get_penalty_service),
) -> ResponseMessage:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    await service.update_penalty_annotation(data)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated"
    )

@router.get("/loss_owners", status_code=status.HTTP_200_OK,
            description="Список доступных владельцев потерь")
async def get_all_loss_owners(
        user: UserPermissions = Depends(get_info_from_token),
) -> list[dict[str, int | str]]:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    return [
        {"id": owner.id, "loss_owner": owner.value_for_db}
        for owner in LossOwnerEnum
    ]

@router.put("/penalty_annotation_from_excel", status_code=status.HTTP_200_OK,
              description="Обновление аннотаций к штрафам с Excel файла")
async def update_penalty_annotations_from_excel(
    upload_file: UploadFile = File(...),
    user: UserPermissions = Depends(get_info_from_token),
    service: PenaltyService = Depends(get_penalty_service)
) -> ResponseMessage:
    if not user.viewing:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="permission locked")
    await service.update_penalty_annotations_from_excel(upload_file=upload_file)
    return ResponseMessage(
        status=status.HTTP_200_OK,
        message="Penalty annotations successfully updated"
    )