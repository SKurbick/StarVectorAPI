import datetime
from typing import List

from asyncpg import Pool
from app.domain.models import OrdersRevenues


class OrdersRevenuesRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_data_by_date(self, date: datetime.date) -> List[OrdersRevenues]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM orders_revenues WHERE date = $1", date)
            return [OrdersRevenues(**row) for row in rows]

    # async def get_all_card_data(self) -> List[CardData]:
    #     async with self.pool.acquire() as conn:
    #         rows = await conn.fetch("SELECT * FROM card_data ")
    #
    #         return [CardData(**row) for row in rows]
