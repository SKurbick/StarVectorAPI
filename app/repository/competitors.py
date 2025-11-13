from typing import Any
from clickhouse_connect.driver.asyncclient import AsyncClient as AsyncClickHouseClient

from app.domain.models import CompetitorResponseModel


class CompetitorsRepository:
    def __init__(self, client: AsyncClickHouseClient):
        self.client = client

    async def _raw_query(self, query: str) -> list[list[Any]]:
        raw_query = await self.client.query(query)
        return raw_query.result_set

    async def get_competitors(self) -> list[CompetitorResponseModel]:
        query = """SELECT
           pp.processed_at AS "дата",
           pp.article_id AS "Наш артикул",
           pp.found_article AS "Артикул конкурента",
           pp.price AS "цена конкурента",
           pp.wild,
           pp.position AS "Позиция в полках конкурента",
           pp.concurrent AS "Конкурент"
        FROM product_positions pp
        WHERE pp.processed_at >= now()
        AND `цена конкурента` IS NOT NULL
        AND "Конкурент" IS NOT NULL
        ORDER BY "дата";"""
        
        result = await self.client.query(query)
        competitors_data = [
            CompetitorResponseModel(
                date=row[0].strftime("%Y-%m-%d %H:%M:%S"),
                article_id=row[1],
                found_article=row[2],
                price=row[3],
                wild=row[4],
                position=row[5],
                competitor=row[6]
            )
            for row in result.result_rows
        ]
        return competitors_data