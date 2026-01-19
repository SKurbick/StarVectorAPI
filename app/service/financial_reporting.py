from openpyxl.pivot import record

from app.repository.financial_reporting import FinancialReportingRepository
from app.domain.models import ItemizationOfExpenses


class FinancialReportingService:
    def __init__(self, repository: FinancialReportingRepository) -> None:
        self.repository = repository

    async def get_items_of_expenses(self, period: str) -> list[ItemizationOfExpenses]:
        records = await self.repository.get_items_of_expenses(period)

        return [
            ItemizationOfExpenses(
                period=record.get("period"),
                category=record.get("category"),
                total_value=record.get("total_value")
            ) for record in records
        ]
