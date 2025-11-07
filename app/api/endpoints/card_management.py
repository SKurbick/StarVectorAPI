from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.models import ResponseMessageDetails, CardUseCaseMetadataResponse
from app.domain.use_cases_registry import MANAGE_CARD_UC_REGISTRY
from app.dependencies.card_management import get_card_use_case
from app.use_cases.card_use_cases import BaseCardUseCase


router = APIRouter(tags=["Cards Management"], prefix="/manage-cards")


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def manage_cards(
    use_case_data: tuple[BaseCardUseCase, dict] = Depends(get_card_use_case)
) -> ResponseMessageDetails:
    """
    Получает запрос на выполнение сценария.
    """
    try:
        use_case, settings = use_case_data
        detail = await use_case.execute(**settings)

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


@router.get("/use-cases", response_model=list[CardUseCaseMetadataResponse])
async def get_available_use_cases():
    """
    Возвращает список доступных сценариев управления карточками.
    """
    return [{"id": i, "use_case": use_case} for i, use_case in enumerate(MANAGE_CARD_UC_REGISTRY)]
