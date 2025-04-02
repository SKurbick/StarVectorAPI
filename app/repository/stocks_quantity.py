from collections import defaultdict
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

    async def update_fbs_data(self, data):
        """Вставка или обновление виртуальных остатков по sku"""
        query = """
        INSERT INTO current_stocks_quantity (article_id, barcode, quantity_type, quantity, updated_data_time)
        SELECT a.nm_id, $2::varchar(20), $3::varchar(250), $4::integer, $5::timestamp
        FROM article a
        WHERE a.account = $1::text -- связь через account
        AND EXISTS (
        SELECT 1 
        FROM current_stocks_quantity c 
        WHERE c.article_id = a.nm_id 
          AND c.barcode = $2::varchar(20) -- barcode из входных данных
        )
        ON CONFLICT (article_id, quantity_type, barcode) 
        DO UPDATE SET
        quantity = EXCLUDED.quantity,
        updated_data_time = EXCLUDED.updated_data_time;                 
         """
        async with self.pool.acquire() as conn:
            await conn.executemany(query, data)
