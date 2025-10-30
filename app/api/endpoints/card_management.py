from fastapi import APIRouter, Depends

from app.domain.models import ManageCardsRequest, ResponseMessage
from app.dependencies.card_management import get_scenario_service
from app.service.card_scenarios.base import BaseCardService


router = APIRouter(tags=["Cards Management"])


@router.post("/manage-cards")
async def manage_cards(service: BaseCardService = Depends(get_scenario_service)) -> ResponseMessage:
    result = await service.execute()
    return ResponseMessage(
        status=202,
        message=result
    )
