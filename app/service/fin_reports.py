from app.repository.fin_reports import FinReportsRepository
from app.domain.models import WeekleFinReportsAggregated


class FinReportsService:
    def __init__(self, repository: FinReportsRepository):
        self.repository = repository

    async def get_fin_reports_aggregated(self) -> list[WeekleFinReportsAggregated]:
        return await self.repository.get_fin_reports_aggregated()
