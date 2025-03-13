from collections import defaultdict
from typing import List

from asyncpg import Pool
from app.domain.models import NetProfitResponseModel, PeriodRequestModel


class NetProfitRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_data_by_period(self, period: PeriodRequestModel) -> List[NetProfitResponseModel]:
        async with self.pool.acquire() as conn:

            query = """
            SELECT 
                article_id, 
                date, 
                SUM(sum_net_profit) AS sum_snp
            FROM 
                accurate_net_profit_data
            WHERE 
                date BETWEEN $1 AND $2
            GROUP BY 
                article_id, 
                date
            ORDER BY 
                sum_snp DESC;"""
            rows = await conn.fetch(query, period.date_from, period.date_to)
            grouped_data = defaultdict(list)
            for record in rows:
                article_id = record["article_id"]
                grouped_data[article_id].append(
                    {"date": record["date"], "net_profit": record["sum_snp"]}
                )

            # Создание объектов ArticleProfit
            response_data = [
                NetProfitResponseModel(article_id=article_id, data=grouped_data[article_id])
                for article_id in grouped_data
            ]

            return response_data

