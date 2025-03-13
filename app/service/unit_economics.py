from typing import List

from app.repository.unit_economics import UnitEconomicsRepository
from app.domain.models import UnitEconomics


class UnitEconomicsService:
    def __init__(self, unit_economics_repository: UnitEconomicsRepository):
        self.unit_economics_repository = unit_economics_repository

    async def get_data_by_article_id(self, article_id: int) -> UnitEconomics:
        return await self.unit_economics_repository.get_data_by_article_id(article_id)

    async def get_current_data(self) -> List[UnitEconomics]:
        return await self.unit_economics_repository.get_all_data()
