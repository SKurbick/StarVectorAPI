from app.service.card_scenarios.close_card import CloseCardService
from app.service.card_scenarios.base import BaseCardService


class ScenarioServiceFactory:
    def __init__(self):
        self.services: dict[str, BaseCardService] = {
            "close_card": CloseCardService,
        }

    def get_service(self, scenario_type: str) -> BaseCardService:
        service_class = self.services.get(scenario_type)

        if not service_class:
            raise ValueError(f"Неизвестный сценарий: {scenario_type}")

        return service_class
