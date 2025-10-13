from datetime import date
from typing import Optional

from asyncpg import Pool

from app.domain.models import MonthlyCategorySales


class SaleRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_categories_sales_per_month(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[MonthlyCategorySales]:
        """Получить результаты продаж по категориям и месяцам."""
        query = """
            SELECT
                month_num,
                subject_name,
                SUM(orders_sum_rub) AS total_revenue,
                SUM(orders_count) AS total_orders_count,
                SUM(sales_sum) AS total_sales_sum,
                CASE
                    WHEN SUM(orders_count) = 0 THEN NULL
                    ELSE ROUND(SUM(orders_sum_rub) / SUM(orders_count), 2)
                END AS average_receipt,
                SUM(profit_by_cond_orders) - SUM(adv_spend) AS net_profit_from_orders,
                CASE
                    WHEN SUM(orders_sum_rub) = 0 THEN NULL
                    ELSE ROUND((SUM(profit_by_cond_orders) - SUM(adv_spend)) / SUM(orders_sum_rub), 3)
                END AS margin
            FROM
                public.orders_articles_analyze
            WHERE
                1 = 1
        """

        end_query = """
            GROUP BY
                month_num,
                subject_name
            ORDER BY
                month_num,
                subject_name;
        """

        params = []

        if start_month and end_month:
            start_year, start_month_num = map(int, start_month.split("-"))
            end_year, end_month_num = map(int, end_month.split("-"))

            params_count = len(params)

            query += f"""
                AND (
                    (EXTRACT(YEAR FROM date) = ${params_count + 1} AND EXTRACT(MONTH FROM date) >= ${params_count + 2})
                    OR EXTRACT(YEAR FROM date) > ${params_count + 1}
                )
                AND (
                    (EXTRACT(YEAR FROM date) = ${params_count + 3} AND EXTRACT(MONTH FROM date) <= ${params_count + 4})
                    OR EXTRACT(YEAR FROM date) < ${params_count + 3}
                )
            """

            params.extend((start_year, start_month_num, end_year, end_month_num))
        else:
            query += f" AND EXTRACT(YEAR FROM date) = {date.today().year}"

        if category:
            query += f" AND subject_name = ${len(params) + 1}"
            params.append(category)

        query += end_query

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [MonthlyCategorySales(**row) for row in rows]
