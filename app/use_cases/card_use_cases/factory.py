from app.use_cases.card_use_cases.base import BaseCardUseCase
from app.use_cases.card_use_cases.open_card_use_case import OpenCardUseCase
from app.use_cases.card_use_cases.close_card_use_case import CloseCardUseCase


class CardUseCaseFactory:
    def __init__(self):
        self.use_cases: dict[str, BaseCardUseCase] = {
            "close_card": CloseCardUseCase,
            "open_card":  OpenCardUseCase,
        }

    def get_use_case(self, use_case_title: str) -> BaseCardUseCase:
        use_case_class = self.use_cases.get(use_case_title)

        if not use_case_class:
            raise ValueError(f"Неизвестный сценарий: {use_case_title}")

        return use_case_class
