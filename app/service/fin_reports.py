from typing import Optional

from app.domain.models import WeeklyFinReportsAggregated, PeriodRequestModel
from app.repository.fin_reports import FinReportsRepository


class FinReportsService:
    def __init__(self, repository: FinReportsRepository):
        self.repository = repository

    async def get_fin_reports_aggregated(
        self,
        period: PeriodRequestModel,
        number_of_last_weeks: Optional[int],
    ) -> list[WeeklyFinReportsAggregated]:
        return await self.repository.get_fin_reports_aggregated(period, number_of_last_weeks)
