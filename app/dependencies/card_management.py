from fastapi import Depends

from asyncpg import Pool

from app.dependencies.database import get_pool
from app.domain.models import ManageCardsRequest
from app.use_cases.card_use_cases import CardUseCaseFactory
from app.use_cases.card_use_cases import BaseCardUseCase


def get_card_use_case_factory() -> CardUseCaseFactory:
    return CardUseCaseFactory()


async def get_card_use_case(
    manage_cards_request: ManageCardsRequest,
    factory: CardUseCaseFactory = Depends(get_card_use_case_factory),
    pool: Pool = Depends(get_pool),
) -> list[BaseCardUseCase]:
    nm_ids = manage_cards_request.nm_ids or []
    local_vendor_codes = manage_cards_request.local_vendor_codes or []

    use_case = factory.get_use_case(manage_cards_request.use_case.title)
    return use_case(
        nm_ids=nm_ids,
        local_vendor_codes=local_vendor_codes,
        pool=pool,
    ), manage_cards_request.settings or {}
