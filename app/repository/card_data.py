from typing import List

from asyncpg import Pool
from app.domain.models import CardData


class CardDataRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_card_data_by_article_id(self, article_id: int) -> CardData:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM card_data WHERE article_id = $1", article_id)
            return CardData(**row) if row else None

    async def get_all_card_data(self) -> List[CardData]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM card_data ")

            return [CardData(**row) for row in rows]
