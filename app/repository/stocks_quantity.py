from collections import defaultdict
from pprint import pprint
from typing import List

from asyncpg import Pool
from app.domain.models import StocksQuantity


class StocksQuantityRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_all_data(self) -> List[StocksQuantity]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM current_stocks_quantity"
            rows = await conn.fetch(query)
            grouped_data = defaultdict(dict)
            for record in rows:
                article_id = record["article_id"]
                grouped_data[article_id].update(
                    {record["quantity_type"]: record['quantity']})

            # Создание объектов OrdersRevenuesResponseModel
            response_data = [
                StocksQuantity(article_id=article_id, data=grouped_data[article_id])
                for article_id in grouped_data
            ]
            return response_data
