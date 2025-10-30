from app.service.card_scenarios.base import BaseCardService


class CloseCardService(BaseCardService):
    async def execute(self) -> None:
        return "Сценарий закрытия карточек выполняем"
