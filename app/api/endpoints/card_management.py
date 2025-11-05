from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ResponseMessageDetails, UseCaseMetadata
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


@router.get("/use-cases", response_model=list[UseCaseMetadata])
async def get_available_use_cases():
    """
    Возвращает список доступных сценариев управления карточками.
    """
    return [
        UseCaseMetadata(
            title="Закрытие карточки",
            name="close_card",
            description="Закрывает карточку: запрещает редактирование остатков и обнуляет виртуальные остатки на маркетплейсе.",
            settings_schema=None,
            example={"title": "close_card"}
        ),
        UseCaseMetadata(
            title="Открытие карточки",
            name="open_card",
            description="Открывает ранее закрытую карточку, разрешая редактирование остатков.",
            settings_schema=None,
            example={"title": "open_card"}
        ),
    ]
