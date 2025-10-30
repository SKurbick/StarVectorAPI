from fastapi import Depends

from asyncpg import Pool

from app.dependencies.database import get_pool
from app.domain.models import ManageCardsRequest
from app.service.card_scenarios.factory import ScenarioServiceFactory
from app.service.card_scenarios.base import BaseCardService


def get_scenario_factory() -> ScenarioServiceFactory:
    return ScenarioServiceFactory()


async def get_scenario_service(
    manage_cards_request: ManageCardsRequest,
    factory: ScenarioServiceFactory = Depends(get_scenario_factory),
    pool: Pool = Depends(get_pool),
) -> list[BaseCardService]:
    nm_ids = manage_cards_request.nm_ids or []
    local_vendor_codes = manage_cards_request.local_vendor_codes or []

    service = factory.get_service(manage_cards_request.scenario.title)
    return service(
        nm_ids=nm_ids,
        local_vendor_codes=local_vendor_codes,
        pool=pool,
    )
