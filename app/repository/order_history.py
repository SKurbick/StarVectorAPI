from datetime import date
from asyncpg import Pool, PostgresError, InterfaceError, ConnectionFailureError, ConnectionDoesNotExistError

from app.domain.models import OrderHistoryResponseModel
from app.utils.decorators import error_handler_http


class OrderHistoryRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    @error_handler_http(
            status_code=500,
            message='Database error occurred',
            exceptions=(
                PostgresError,
                InterfaceError,
                ConnectionFailureError,
                ConnectionDoesNotExistError
            )
    )
    async def get_orders_history(
            self,
            product_id: str,
            start: date | None,
            end: date | None
	) -> list[OrderHistoryResponseModel]:
        async with self.pool.acquire() as conn:
            query = """
                WITH aggregated_data AS (
                    SELECT
                        local_vendor_code AS wild,
                        DATE_TRUNC('day', date) AS date_day,
                        SUM(orders_sum_rub) AS total_orders_sum,
                        SUM(orders_count) AS total_orders_count,
                        SUM(profit_by_cond_orders) AS total_profit,
                        SUM(adv_spend) AS total_adv_spend,
                        AVG(purchase_price) AS avg_purchase_price,
                        SUM(views) AS total_views,
                        SUM(clicks) AS total_clicks,
                        SUM(add_to_cart_count) AS total_carts
                    FROM orders_articles_analyze
                    WHERE 
                        local_vendor_code LIKE $1 AND
                        ($2::date IS NULL OR date >= $2::date) AND
                        ($3::date IS NULL OR date <= $3::date)
                    GROUP BY local_vendor_code, DATE_TRUNC('day', date)
                ),
                aggregated_data_with_rolling as (
                    SELECT *,
                    SUM(total_orders_sum) OVER (
                        PARTITION BY wild
                        ORDER BY date_day
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS total_orders_sum_7d,
                    AVG(total_orders_sum) OVER (
                        PARTITION BY wild
                        ORDER BY date_day
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS avg_orders_sum_7d,
                    SUM(total_orders_count) OVER (
                        PARTITION BY wild
                        ORDER BY date_day
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS total_orders_count_7d,
                    AVG(total_orders_count) OVER (
                        PARTITION BY wild
                        ORDER BY date_day
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW 
                    ) AS avg_orders_count_7d
                    FROM aggregated_data
                ),
                balance_agg AS (
                    SELECT
                        product_id,
                        ROUND(AVG(physical_quantity)) AS avg_physical_quantity
                    FROM balance_history
                    GROUP BY product_id
                ),
                article_sales AS (
                    SELECT DISTINCT
                        local_vendor_code AS wild,
                        DATE_TRUNC('day', date) AS date_day,
                        article_id
                    FROM orders_articles_analyze
                    WHERE 
                        ($2::date IS NULL OR date >= $2::date) AND
                        ($3::date IS NULL OR date <= $3::date)
                ),
                wb_stock_aggregated AS (
                    SELECT
                        asl.wild,
                        asl.date_day,
                        SUM(ws.quantity_full) AS total_wb_quantity
                    FROM article_sales asl
                    LEFT JOIN wb_stock ws ON asl.article_id = ws.nm_id
                    GROUP BY asl.wild, asl.date_day
                )
                SELECT
                    ad.wild AS product_id,
                    TO_CHAR(ad.date_day, 'YYYY-MM-DD') as date,
                    ad.total_orders_sum AS total_orders_sum,
                    ad.total_orders_sum_7d,
                    ROUND(ad.avg_orders_sum_7d, 0) as avg_sum_rub_7d,
                    ad.total_orders_count AS total_orders_count,
                    ad.total_orders_count_7d,
                    ROUND(ad.avg_orders_count_7d, 0) AS avg_orders_count_7d,
                    COALESCE(ROUND(ad.total_orders_sum / NULLIF(ad.total_orders_count, 0), 2), 0) AS average_bill,
                    COALESCE(ROUND(ad.total_profit / NULLIF(ad.total_orders_sum, 0), 2), 0) AS marginal,
                    ad.total_profit AS conditional_profit,
                    ad.total_profit - ad.total_adv_spend AS net_profit,
                    COALESCE(ROUND((ad.total_profit - ad.total_adv_spend) / NULLIF(ad.total_orders_sum, 0), 2), 0) AS profitability,
                    ad.avg_purchase_price AS purchase_price,
                    ad.total_adv_spend AS adversting,
                    ad.total_views AS views,
                    ad.total_clicks AS clicks,
                    ad.total_carts AS carts,
                    COALESCE(ROUND(ad.total_adv_spend / NULLIF(ad.total_orders_sum, 0), 2), 0) AS drr,
                    COALESCE(ba.avg_physical_quantity, 0) AS physical_quantity,
                    COALESCE(wb_agg.total_wb_quantity, 0) AS wb_quantity,
                    (ad.total_adv_spend > 0) AS participation_in_adversting
                FROM aggregated_data_with_rolling ad
                LEFT JOIN balance_agg ba ON ad.wild = ba.product_id
                LEFT JOIN wb_stock_aggregated wb_agg ON ad.wild = wb_agg.wild AND ad.date_day = wb_agg.date_day
                ORDER BY ad.date_day DESC;
            """

            rows = await conn.fetch(query, product_id, start, end)
            return [
                OrderHistoryResponseModel(
                    product_id=row["product_id"],
                    date=row["date"],
                    total_orders_sum=row["total_orders_sum"],
                    total_orders_sum_7d=row["total_orders_sum_7d"],
                    avg_sum_rub_7d = row["avg_sum_rub_7d"],
                    total_orders_count=row["total_orders_count"],
                    total_orders_count_7d = row["total_orders_count_7d"],
                    avg_orders_count_7d = row["avg_orders_count_7d"],
                    average_bill=row["average_bill"],
                    marginal=f'{int(row["marginal"] * 100)}%',
                    conditional_profit=row["conditional_profit"],
                    net_profit=row["net_profit"],
                    profitability=f'{int(row["profitability"]* 100)}%',
                    purchase_price=row["purchase_price"],
                    adversting=row["adversting"],
                    views=row["views"],
                    clicks=row["clicks"],
                    carts=row["carts"],
                    drr=f'{int(row["drr"] * 100)}%',
                    physical_quantity=row["physical_quantity"],
                    wb_quantity=row["wb_quantity"],
                    participation_in_adversting = row["participation_in_adversting"]
				) 
                for row in rows
                ]