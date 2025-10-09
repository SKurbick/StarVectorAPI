from datetime import date
from typing import Optional

from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import WeeklyFinReportsAggregated, FinReportDeduction


class FinReportsRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_fin_reports_aggregated(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        number_of_last_weeks: Optional[int] = None,
    ) -> list[WeeklyFinReportsAggregated]:
        main_query = """
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
            fram."Удержания" AS total_deductions,
            fram."Платная приемка" AS paid_acceptance,
            fram."Закупочная стоимость продаж" AS purchase_price_of_sales,
            fram."Закупочная стоимость возвратов" AS purchase_price_of_returns,
            fram."Закупочная стоимость" AS purchase_cost,
            fdm.grouped_bonus_type_name,
            fdm.total_deduction AS deduction
        FROM ({subquery}) fram
        LEFT JOIN fin_deductions_mv fdm
        ON fram.date_from = fdm.date_from
        ORDER BY fram.date_from DESC;
        """

        subquery = """
            SELECT *
            FROM fin_reports_agg_mv
        """

        where_subquery_conditions = []
        params = []

        if date_from:
            where_subquery_conditions.append(f"date_from >= ${len(params) + 1} ")
            params.append(date_from)

        if date_to:
            where_subquery_conditions.append(f"date_from <= ${len(params) + 1} ")
            params.append(date_to)

        if where_subquery_conditions:
            subquery += "WHERE " + "AND ".join(where_subquery_conditions)

        if number_of_last_weeks:
            subquery += f" LIMIT ${len(params) + 1}"
            params.append(number_of_last_weeks)

        result_query = main_query.format(subquery=subquery)

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(result_query, *params)
        except UndefinedTableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table or materialized view not found",
            )

        reports = {}

        for row in rows:
            report_date_from = row["date_from"]

            if not reports.get(report_date_from):
                reports[report_date_from] = dict(
                    date_from=row["date_from"],
                    vb_commission=row["vb_commission"],
                    to_be_transferred=row["to_be_transferred"],
                    logistics=row["logistics"],
                    total_to_be_paid=row["total_to_be_paid"],
                    revenue=row["revenue"],
                    discounted_retail_price=row["discounted_retail_price"],
                    penalty=row["penalty"],
                    storage_fee=row["storage_fee"],
                    paid_acceptance=row["paid_acceptance"],
                    purchase_price_of_sales=row["purchase_price_of_sales"],
                    purchase_price_of_returns=row["purchase_price_of_returns"],
                    purchase_cost=row["purchase_cost"],
                    total_deductions=row["total_deductions"],
                    deductions=[],
                )

            reports[report_date_from]["deductions"].append(
                FinReportDeduction(
                    grouped_bonus_type_name=row["grouped_bonus_type_name"],
                    total_deduction=row["deduction"],
                )
            )

        return [
            WeeklyFinReportsAggregated(**report) for report in reports.values()
        ]
