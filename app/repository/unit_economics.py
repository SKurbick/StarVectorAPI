from typing import List

from asyncpg import Pool
from app.domain.models import UnitEconomics


class UnitEconomicsRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_data_by_article_id(self, article_id: int) -> UnitEconomics:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM unit_economics WHERE article_id = $1", article_id)
            return UnitEconomics(**row) if row else None

    async def get_all_data(self) -> List[UnitEconomics]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM unit_economics")

            return [UnitEconomics(**row) for row in rows]
