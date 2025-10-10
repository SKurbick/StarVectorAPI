from typing import Optional
from datetime import date

from app.repository.fin_reports import FinReportsRepository
from app.domain.models import WeeklyFinReportsAggregated, DaylyPenaltiesReport


class FinReportsService:
    def __init__(self, repository: FinReportsRepository):
        self.repository = repository

    async def get_fin_reports_aggregated(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        number_of_last_weeks: Optional[int],
    ) -> list[WeeklyFinReportsAggregated]:
        return await self.repository.get_fin_reports_aggregated(date_from, date_to, number_of_last_weeks)

    async def get_penalties_details(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        limit: Optional[int],
        offset: Optional[int],
    ) -> list[DaylyPenaltiesReport]:
        return await self.repository.get_penalties_details(date_from, date_to, limit, offset)
