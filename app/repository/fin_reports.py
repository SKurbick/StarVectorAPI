from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import WeekleFinReportsAggregated, ResponseMessage


class FinReportsRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_fin_reports_aggregated(self) -> list[WeekleFinReportsAggregated]:
        query = """
        SELECT
            fram.date_from,
            fram."Комиссия ВБ" AS vb_commission,
            fram."К перечислению" AS to_be_transferred,
            fram."Логистика" AS logistics,
            fram."Итого к оплате" AS total_to_be_paid,
            fram."Выручка" AS revenue,
            fram."Розничная цена со скидкой" AS discounted_retail_price,
            fram."Штрафы" AS penalty,
            fram."Хранение" AS storage_fee,
            fram."Удержания" AS total_deduction,
            fdm.grouped_bonus_type_name,
            fram."Платная приемка" AS paid_acceptance,
            fram."Закупочная стоимость продаж" AS purchase_price_of_sales,
            fram."Закупочная стоимость возвратов" AS purchase_price_of_returns,
            fram."Закупочная стоимость" AS purchase_cost
        FROM fin_reports_agg_mv fram 
        LEFT JOIN fin_deductions_mv fdm
        ON fram.date_from = fdm.date_from
        ORDER BY fram.date_from DESC;
        """

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
        except UndefinedTableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table or materialized view not found",
            )

        return [WeekleFinReportsAggregated(**row) for row in rows]
