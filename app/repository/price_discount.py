from typing import List

from asyncpg import Pool
from app.domain.models import PriceDiscountResponseModel, PriceDiscountDB


class PriceDiscountRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def update(self, update_data: PriceDiscountDB):
        async with self.pool.acquire() as conn:
            # todo update запрос
            pass
