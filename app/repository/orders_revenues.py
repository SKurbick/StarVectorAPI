import datetime
from collections import defaultdict
from typing import List

from asyncpg import Pool
from app.domain.models import PeriodRequestModel, OrdersRevenuesResponseModel


class OrdersRevenuesRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_data_by_period(self, period: PeriodRequestModel) -> List[OrdersRevenuesResponseModel]:
        async with self.pool.acquire() as conn:
            query = """
            SELECT * FROM orders_revenues
            WHERE 
                date BETWEEN $1 AND $2;
            """
            rows = await conn.fetch(query, period.date_from, period.date_to)
            grouped_data = defaultdict(list)
            for record in rows:
                article_id = record["article_id"]
                grouped_data[article_id].append(
                    {"date": record['date'],
                     "orders_sum_rub": record['orders_sum_rub'],
                     "orders_count": record['orders_count'],
                     "open_card_count": record['open_card_count'],
                     "add_to_cart_count": record['add_to_cart_count'],
                     "buyouts_count": record['buyouts_count'],
                     "buyouts_sum_rub": record['buyouts_sum_rub'],
                     "cancel_count": record['cancel_count'],
                     "cancel_sum_rub": record['cancel_sum_rub']})
            # Создание объектов OrdersRevenuesResponseModel
            response_data = [
                OrdersRevenuesResponseModel(article_id=article_id, data=grouped_data[article_id])
                for article_id in grouped_data
            ]

            return response_data
