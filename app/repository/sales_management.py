from datetime import date
from typing import Optional, Sequence

from asyncpg import Pool


class SalesManagementRepository:
    """Репозиторий для GoogleDocs `Панель управления продажами Вектор`"""

    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def get_sums_ic_and_revenue_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
    ) -> Sequence:
        """Получить суммы прибыли по индивидуальным условиям по категориям"""
        params = [end_date, start_date]
        query = """
                WITH aggregated_orders_revenues AS (SELECT article_id,
                                                           SUM(orders_sum_rub) AS total_revenue,
                    date
                FROM orders_revenues
                GROUP BY article_id, date
                    )
                SELECT cd.subject_name,
                       SUM(anpc.sum_net_profit) AS ic,
                       SUM(aor.total_revenue)   AS revenue,
                       anpc."date"
                FROM accurate_npd_purchase_calculation anpc
                         JOIN card_data cd ON cd.article_id = anpc.article_id
                         JOIN aggregated_orders_revenues aor
                              ON anpc.article_id = aor.article_id AND anpc."date" = aor."date"
                WHERE anpc."date" BETWEEN $1 AND $2
                GROUP BY cd.subject_name, anpc."date"
                ORDER BY anpc."date" DESC, ic DESC;
                """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_sums_ic_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            period: int
    ):
        """Получить AVG IC за прошлый период"""
        params = [end_date, start_date, period]
        query = """
                SELECT cd.subject_name, ROUND((SUM(anpc.sum_net_profit) / $3), 0) AS ic
                FROM accurate_npd_purchase_calculation anpc
                         JOIN card_data AS cd ON cd.article_id = anpc.article_id
                WHERE anpc."date" BETWEEN $1 AND $2
                GROUP BY cd.subject_name
                ORDER BY ic DESC, ic DESC \
                """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_sums_sales_by_category_and_period(
            self,
            date_start: date,
            date_end: date,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить суммы продаж по дням и категориям и SKU"""
        params = [date_end, date_start]
        query = """SELECT cd.subject_name,
                          SUM(t.orders_sum_rub) AS summ,
                          t."date",
                          CASE
                              WHEN SUM(CASE WHEN COALESCE(t.orders_sum_rub, 0) = 0 THEN 1 ELSE 0 END) +
                                   SUM(CASE WHEN t.orders_sum_rub > 0 THEN 1 ELSE 0 END) > 0
                                  THEN ROUND(CAST(SUM(CASE WHEN t.orders_sum_rub > 0 THEN 1 ELSE 0 END) AS DECIMAL) /
                                             (SUM(CASE WHEN COALESCE(t.orders_sum_rub, 0) = 0 THEN 1 ELSE 0 END) +
                                              SUM(CASE WHEN t.orders_sum_rub > 0 THEN 1 ELSE 0 END)), 2) * 100
                              ELSE 0
                              END               AS sku_percentage
                   FROM orders_revenues t
                            JOIN card_data cd ON t.article_id = cd.article_id
                   WHERE t."date" BETWEEN $1 AND $2"""
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $5 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name, t."date"
                    ORDER BY t."date" ASC, summ DESC """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_managers_name_by_category_and_period(
            self,
            date_start: date,
            date_end: date,
            good_category: Optional[str] = None,
    ):
        """Получить имена менеджеров из промок, по дате и категории"""
        params = [date_end, date_start]
        query = """SELECT pami.manager, cd.subject_name, pami."date"
                   FROM card_data cd
                            JOIN promo_and_managers_info pami ON pami.nm_id = cd.article_id
                   WHERE DATE BETWEEN $1
                     AND $2"""
        if good_category is not None:
            query += f" AND cd.subject_name LIKE $2 "
            params.append(f"%{good_category}%")
        query += f""" GROUP BY pami.manager, cd.subject_name, pami."date" """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_sums_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            # TODO need fix AVG math and naming
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить AVG по прошлому периоду по категориям"""
        params = [end_date, start_date]
        query = """SELECT cd.subject_name, (SUM(t.orders_sum_rub) / 7) AS summ
                   FROM orders_revenues t
                            JOIN card_data cd ON t.article_id = cd.article_id
                   WHERE t."date" BETWEEN $1 and $2
                """
        if good_category is not None:
            """AND cd.subject_name LIKE $2"""
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name
                              ORDER BY summ DESC """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_sum_sales_by_date(
            self,
            date: date,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить общую сумму по продажам за день с опциональным фильтром по категориям"""
        params = [date] if good_category is None else [date, f"%{good_category}%"]
        query_sums = """
                     SELECT cd.subject_name, SUM(t.orders_sum_rub) AS summ, t."date"
                     FROM orders_revenues t
                              JOIN card_data cd ON t.article_id = cd.article_id
                     WHERE t."date" = $1 \
                     """
        if good_category is not None:
            query_sums += """ AND cd.subject_name LIKE $2 """
        query_sums += """ GROUP BY cd.subject_name, t."date"
                     ORDER BY t."date" ASC, summ DESC 
                     """
        async with self.pool.acquire() as conn:
            r_suum_sales_date = await conn.fetch(query_sums, *params)
        return r_suum_sales_date
