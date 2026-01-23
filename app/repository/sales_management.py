from datetime import date
from typing import Optional, Sequence

from asyncpg import Pool


class SalesManagementRepository:
    """Репозиторий для GoogleDocs `Панель управления продажами Вектор`"""

    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def get_shares_goods(self, is_promotion: bool) -> Sequence:
        """Получить товары в акциях или без"""
        query = """
                SELECT p.nm_id,
                       a.local_vendor_code,
                       a.account,
                       cd.subject_name,
                       p.plan_price,
                       (cd.price - (cd.price * cd.discount / 100)) AS real_price,
                       p.promo_name
                FROM promotions p
                         JOIN card_data cd ON cd.article_id = p.nm_id
                         JOIN article a ON p.nm_id = a.nm_id
                """
        if is_promotion:
            query += """ WHERE p.plan_price > (cd.price - (cd.price * cd.discount / 100)); """
        else:
            query += """ WHERE p.plan_price < (cd.price - (cd.price * cd.discount / 100)); """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
        return rows


    async def get_shares_total_items_by_accounts(self) -> Sequence:
        """Получить количество товаров и товаров с акциями по аккаунтам"""
        query = """
                WITH account_aggregator AS (SELECT a.account,
                                                   COUNT(DISTINCT p.nm_id) AS total_items
                                            FROM article a
                                                     JOIN promotions p ON p.nm_id = a.nm_id
                                            where NOW() BETWEEN p.created_at AND p.promo_end
                                            GROUP BY a.account)
                SELECT a.account,
                       COUNT(DISTINCT p.nm_id)                                    AS promotion_items,
                       aa.total_items,
                       ROUND(COUNT(DISTINCT p.nm_id) * 100.0 / aa.total_items, 2) AS percentage
                FROM promotions p
                         JOIN article a ON a.nm_id = p.nm_id
                         JOIN card_data cd ON cd.article_id = p.nm_id
                         JOIN account_aggregator aa ON aa.account = a.account
                WHERE p.plan_price > (cd.price * (1 - cd.discount / 100.0))
                  AND NOW() BETWEEN p.promo_start AND p.promo_end
                GROUP by a.account, aa.total_items
                ORDER by a.account DESC;
                """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
        return rows

    async def get_manager_with_category_without_date(
            self,
            start_date: date,
            end_date: date,
    ) -> Sequence:
        """Получить менеджеров по категориям без дат"""
        params = [end_date, start_date]
        query = """
                SELECT pami.manager, cd.subject_name
                FROM card_data cd
                         JOIN promo_and_managers_info pami ON pami.nm_id = cd.article_id
                WHERE DATE BETWEEN $1
                  AND $2 AND cd.subject_name IS NOT NULL 
                GROUP BY pami.manager, cd.subject_name
                ORDER BY cd.subject_name;
                """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows


    async def get_penalty_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить штрафы по категориям за период"""
        params = [end_date, start_date]
        query = """
                SELECT dfrf.subject_name, round(sum(dfrf.penalty), 0) AS penalty, dfrf.date_from AS date
                FROM daily_fin_reports_full dfrf
                WHERE dfrf.date_from BETWEEN $1
                  AND $2
                """
        if good_category is not None:
            query += """ AND dfrf.subject_name LIKE $3 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY dfrf.subject_name, dfrf.date_from; """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_outlay_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить затраты по категориям за период"""
        params = [end_date, start_date]
        query = """
                SELECT cd.subject_name,
                       SUM(upd_sum) AS adv_spend,
                       as2."date"
                FROM advert_spend asn
                         LEFT JOIN (SELECT campaign_id,
                                           article_id,
                                           "date"
                                    FROM advert_stat) as2
                                   ON as2.campaign_id = asn.advert_id
                                       AND as2."date" = asn."date"
                         LEFT JOIN card_data cd
                                   ON cd.article_id = as2.article_id
                WHERE as2."date" BETWEEN $1 AND $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $3 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY as2."date", cd.subject_name
                ORDER BY "date" DESC; """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_outlay_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            period: int,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить AVG затрат по категориям за прошлый период"""
        params = [end_date, start_date, period]
        query = """
                SELECT cd.subject_name,
                       round(SUM(upd_sum) / $3, 0) AS adv_spend
                FROM advert_spend asn
                         LEFT JOIN (SELECT campaign_id,
                                           article_id,
                                           "date"
                                    FROM advert_stat) as2
                                   ON as2.campaign_id = asn.advert_id
                                       AND as2."date" = asn."date"
                         LEFT JOIN card_data cd
                                   ON cd.article_id = as2.article_id
                WHERE as2."date" BETWEEN $1 AND $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $4 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name
                ORDER BY cd.subject_name; """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_browsing_info_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить просмотры и клики на товары по категориям за период"""
        params = [end_date, start_date]
        query = """
                SELECT cd.subject_name,
                       sum(t."views")          AS views,
                       CASE
                           WHEN sum(t."views") > 0
                               THEN round(sum(t.clicks) / sum(t."views") * 100, 2)
                           ELSE 0 END          AS clicks,
                       round(avg(t.clicks), 0) AS clicks_avg,
                       t."date"
                FROM advert_stat t
                         JOIN card_data cd ON t.article_id = cd.article_id
                WHERE t."date" BETWEEN $1 AND $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $3 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name, t."date"
                ORDER BY cd.subject_name, t."date" DESC; """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_browsing_info_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            period: int,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить AVG просмотры и клики на товары по категориям за прошлы период"""
        params = [end_date, start_date, period]
        query = """
                select cd.subject_name,
                       round(sum(t."views") / $3, 0) as views,
                       case
                           when sum(t."views") > 0 then round(sum(t.clicks) / sum(t."views") * 100, 2)
                           else 0 end                as clicks,
                       round(avg(t.clicks), 0)       as clicks_avg
                from advert_stat as t
                         join card_data as cd on cd.article_id = t.article_id
                where t."date" between $1 and $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $4 """
            params.append(f"%{good_category}%")
        query += """ group by cd.subject_name;"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_sums_ic_and_revenue_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            good_category: Optional[str] = None,
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
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $3 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name, anpc."date"
                ORDER BY anpc."date" DESC, ic DESC;"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_sums_ic_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            period: int,
            good_category: Optional[str] = None,
    ):
        """Получить AVG IC за прошлый период"""
        params = [end_date, start_date, period]
        query = """
                SELECT cd.subject_name, ROUND((SUM(anpc.sum_net_profit) / $3), 0) AS ic
                FROM accurate_npd_purchase_calculation anpc
                         JOIN card_data AS cd ON cd.article_id = anpc.article_id
                WHERE anpc."date" BETWEEN $1 AND $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $4 """
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name
                ORDER BY ic DESC """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_sums_revenue_by_category_and_period(
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
            query += """ AND cd.subject_name LIKE $3 """
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
            query += f" AND cd.subject_name LIKE $3 "
            params.append(f"%{good_category}%")
        query += f""" GROUP BY pami.manager, cd.subject_name, pami."date" """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_old_sums_revenue_by_category_and_period(
            self,
            start_date: date,
            end_date: date,
            period: int,
            good_category: Optional[str] = None,
    ) -> Sequence:
        """Получить AVG по прошлому периоду по категориям"""
        params = [end_date, start_date, period]
        query = """SELECT cd.subject_name, (SUM(t.orders_sum_rub) / $3) AS summ
                   FROM orders_revenues t
                            JOIN card_data cd ON t.article_id = cd.article_id
                   WHERE t."date" BETWEEN $1 and $2
                """
        if good_category is not None:
            query += """ AND cd.subject_name LIKE $4"""
            params.append(f"%{good_category}%")
        query += """ GROUP BY cd.subject_name
                              ORDER BY summ DESC """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return rows

    async def get_sum_revenue_by_date(
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
