from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ResponseMessageDetails
from app.dependencies.card_management import get_scenario_service
from app.service.card_scenarios.base import BaseCardService


router = APIRouter(tags=["Cards Management"])


@router.post("/manage-cards", status_code=status.HTTP_202_ACCEPTED)
async def manage_cards(service: BaseCardService = Depends(get_scenario_service)) -> ResponseMessageDetails:
    try:
        detail = await service.execute()
        return ResponseMessageDetails(
            status=202,
            message="Запрос на управление карточками принят",
            detail=detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Не удалось выполнить сценарий: {e}"
        )
