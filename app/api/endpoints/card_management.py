from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ResponseMessageDetails
from app.dependencies.card_management import get_card_use_case
from app.use_cases.card_use_cases import BaseCardUseCase


router = APIRouter(tags=["Cards Management"])


@router.post("/manage-cards", status_code=status.HTTP_202_ACCEPTED)
async def manage_cards(use_case: BaseCardUseCase = Depends(get_card_use_case)) -> ResponseMessageDetails:
    try:
        detail = await use_case.execute()
        return ResponseMessageDetails(
            status=status.HTTP_202_ACCEPTED,
            message="Запрос на управление карточками принят",
            details=detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Не удалось выполнить сценарий: {e}"
        )
