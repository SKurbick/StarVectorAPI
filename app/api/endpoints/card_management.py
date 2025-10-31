from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ResponseMessage
from app.dependencies.card_management import get_scenario_service
from app.service.card_scenarios.base import BaseCardService


router = APIRouter(tags=["Cards Management"])


@router.post("/manage-cards", status_code=status.HTTP_202_ACCEPTED)
async def manage_cards(service: BaseCardService = Depends(get_scenario_service)) -> ResponseMessage:
    try:
        await service.execute()
        return ResponseMessage(
            status=202,
            message="Запрос на закрытие карточек получен"
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Error: {e}"
        )
