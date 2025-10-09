from typing import Optional
from datetime import date

from app.repository.fin_reports import FinReportsRepository
from app.domain.models import WeeklyFinReportsAggregated


class FinReportsService:
    def __init__(self, repository: FinReportsRepository):
        self.repository = repository

    async def get_fin_reports_aggregated(
        self, date_to: Optional[date], number_of_last_weeks: Optional[int]
    ) -> list[WeeklyFinReportsAggregated]:
        return await self.repository.get_fin_reports_aggregated(date_to, number_of_last_weeks)
