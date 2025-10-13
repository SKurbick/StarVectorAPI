from app.domain.models import DaylyPenaltiesReport, PeriodRequestModel
from app.repository.penalties import PenaltyRepository


class PenaltyService:
    def __init__(self, repository: PenaltyRepository):
        self.repository = repository

    async def get_penalties_details(
        self,
        period: PeriodRequestModel,
    ) -> list[DaylyPenaltiesReport]:
        """Получить данные о штрафах по каждому дню."""
        return await self.repository.get_penalties_details(period)
