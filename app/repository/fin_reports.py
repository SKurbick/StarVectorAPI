from typing import Optional

from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import WeeklyFinReportsAggregated, FinReportDeduction, PeriodRequestModel


class FinReportsRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_fin_reports_aggregated(
        self,
        period: PeriodRequestModel,
        number_of_last_weeks: Optional[int] = None,
    ) -> list[WeeklyFinReportsAggregated]:
        main_query = """
        SELECT
            fram.date_to,
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
            fram."Перечисления по кредиту" AS credit_transfers,
            fram."К клиенту при отмене" AS to_client_upon_cancellation,
            fram."От клиента при отмене" AS from_client_upon_cancellation,
            fram."От клиента при возврате" AS from_client_upon_return,
            fram."К клиенту при продаже" AS to_client_upon_sale,
            fram."Закупочная стоимость продаж" AS purchase_price_of_sales,
            fram."Закупочная стоимость возвратов" AS purchase_price_of_returns,
            fram."Закупочная стоимость" AS purchase_cost,
            fdm.grouped_bonus_type_name,
            fdm.total_deduction AS deduction
        FROM ({subquery}) fram
        LEFT JOIN fin_deductions_mv fdm
        ON fram.date_to = fdm.date_to
        ORDER BY fram.date_to DESC;
        """

        subquery = """
            SELECT *
            FROM fin_reports_mv
            WHERE date_to BETWEEN $1 AND $2
        """

        params = [period.date_from, period.date_to]

        if number_of_last_weeks:
            subquery += f" LIMIT $3"
            params.append(number_of_last_weeks)

        full_query = main_query.format(subquery=subquery)

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(full_query, *params)
        except UndefinedTableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table or materialized view not found",
            )

        reports = {}

        for row in rows:
            report_date_to = row["date_to"]

            if not reports.get(report_date_to):
                reports[report_date_to] = dict(
                    date_to=row["date_to"],
                    vb_commission=row["vb_commission"],
                    to_be_transferred=row["to_be_transferred"],
                    logistics=row["logistics"],
                    total_to_be_paid=row["total_to_be_paid"],
                    revenue=row["revenue"],
                    discounted_retail_price=row["discounted_retail_price"],
                    penalty=row["penalty"],
                    storage_fee=row["storage_fee"],
                    paid_acceptance=row["paid_acceptance"],
                    credit_transfers=row["credit_transfers"],
                    to_client_upon_cancellation=row["to_client_upon_cancellation"],
                    from_client_upon_cancellation=row["from_client_upon_cancellation"],
                    from_client_upon_return=row["from_client_upon_return"],
                    to_client_upon_sale=row["to_client_upon_sale"],
                    purchase_price_of_sales=row["purchase_price_of_sales"],
                    purchase_price_of_returns=row["purchase_price_of_returns"],
                    purchase_cost=row["purchase_cost"],
                    total_deductions=row["total_deductions"],
                    deductions=[],
                )

            reports[report_date_to]["deductions"].append(
                FinReportDeduction(
                    grouped_bonus_type_name=row["grouped_bonus_type_name"],
                    total_deduction=row["deduction"],
                )
            )

        return [
            WeeklyFinReportsAggregated(**report) for report in reports.values()
        ]
