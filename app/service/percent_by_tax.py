import asyncio
from pprint import pprint
from typing import List, Dict

from app.config.settings import get_wb_tokens
from app.domain.models import PercentByTaxResponseModel, DefaultPercentByTaxResponseModel

from app.repository.percent_by_tax import PercentByTaxRepository


class PercentByTaxService:
    def __init__(
            self,
            percent_by_tax_repository: PercentByTaxRepository,
    ):
        self.percent_by_tax_repository = percent_by_tax_repository

    async def update_tax_by_article_id(self, data: List[PercentByTaxResponseModel]):
        await self.percent_by_tax_repository.update_percent_by_tax(data)

    async def update_default_percent_by_tax(self, data: DefaultPercentByTaxResponseModel):
        await self.percent_by_tax_repository.update_default_percent_by_tax(data)
