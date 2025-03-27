import datetime
from typing import List

from app.repository.turnover import TurnoverRepository
from app.domain.models import TurnoverByFederalDistrictData, TurnoverByFederalDistrict


class TurnoverService:
    def __init__(self, turnover_repository: TurnoverRepository):
        self.turnover_repository = turnover_repository

    async def get_data_by_article_id(self, article_id: int) -> TurnoverByFederalDistrict:
        return await self.turnover_repository.get_data_by_article_id(article_id)

    async def turnover_by_federal_district(self) -> TurnoverByFederalDistrictData:
        start_day = datetime.datetime.today().date() - datetime.timedelta(days=7)
        end_day = datetime.datetime.today().date() - datetime.timedelta(days=1)
        return await self.turnover_repository.turnover_by_federal_district(start_day, end_day)
