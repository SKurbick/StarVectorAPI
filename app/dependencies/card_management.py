from fastapi import Depends

from app.domain.models import ManageCardsRequest
from app.service.card_scenarios.factory import ScenarioServiceFactory
from app.service.card_scenarios.base import BaseCardService


def get_scenario_factory() -> ScenarioServiceFactory:
    return ScenarioServiceFactory()


async def get_scenario_service(
    request: ManageCardsRequest,
    factory: ScenarioServiceFactory = Depends(get_scenario_factory),
) -> list[BaseCardService]:
    nm_ids = request.nm_ids or []
    local_vendor_codes = request.local_vendor_codes or []

    service = factory.get_service(request.scenario.title)
    return service(
        nm_ids=nm_ids,
        local_vendor_codes=local_vendor_codes,
    )
