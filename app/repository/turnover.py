import datetime
from typing import List

from asyncpg import Pool
from app.domain.models import TurnoverByFederalDistrictData, TurnoverByFederalDistrict, transform_asyncpg_data


class TurnoverRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_data_by_article_id(self, article_id: int) -> TurnoverByFederalDistrict:
        pass

    async def turnover_by_federal_district(self, start_date: datetime, end_date: datetime) -> TurnoverByFederalDistrictData:
        async with self.pool.acquire() as conn:
            temp_table_query = """
            CREATE TEMP TABLE temp_avg_data AS
            SELECT
                article_id,
                federal_district,
                ROUND(AVG(orders_count), 2) AS daily_average
            FROM
                orders_by_federal_district
            WHERE
                date BETWEEN $1 AND $2
            GROUP BY
                article_id,
                federal_district;
            """
            select_avg_query = """
            SELECT
                tad.article_id,
                tad.federal_district,
                tad.daily_average,
                csq.quantity,
                CASE
                    WHEN tad.daily_average = 0 THEN NULL
                    ELSE csq.quantity / tad.daily_average
                END AS balance_for_number_of_days
            FROM
                temp_avg_data tad
            JOIN
                current_stocks_quantity  csq
                ON tad.article_id = csq.article_id
                AND tad.federal_district = csq.quantity_type;"""
            async with conn.transaction():
                await conn.execute(temp_table_query, start_date, end_date)
                result = await conn.fetch(select_avg_query)
                await conn.execute("""DROP TABLE temp_avg_data;""")
        transform_data = transform_asyncpg_data(result)
        return TurnoverByFederalDistrictData.model_validate(transform_data)
