from typing import Optional

from app.domain.models import MonthlyCategorySales
from app.repository.sales import SaleRepository


class SaleService:
    def __init__(self, repository: SaleRepository):
        self.repository = repository

    async def get_categories_sales_per_month(
        self,
        start_month: Optional[str],
        end_month: Optional[str],
        category: Optional[str],
    ) -> list[MonthlyCategorySales]:
        """Получить результаты продаж по категориям и месяцам."""
        return await self.repository.get_categories_sales_per_month(start_month, end_month, category)
