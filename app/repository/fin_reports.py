from datetime import date
from typing import Optional

from asyncpg import Pool, UndefinedTableError
from fastapi import HTTPException, status

from app.domain.models import WeeklyFinReportsAggregated, FinReportDeduction, PenaltyDetails, DaylyPenaltiesReport


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
        """

        where_subquery_conditions = []
        params = []

        if date_from:
            where_subquery_conditions.append(f"date_to >= ${len(params) + 1} ")
            params.append(date_from)

        if date_to:
            where_subquery_conditions.append(f"date_to <= ${len(params) + 1} ")
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

    async def get_penalties_details(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[DaylyPenaltiesReport]:
        query = """
        SELECT
            date as penalty_date,
            sale_dt,
            penalty,
            count_items,
            bonus_type_name,
            nm_id,
            subject_name,
            account,
            srid,
            warehouse_type,
            order_date,
            local_vendor_code,
            shk_id,
            assembly_id,
            supplier_status,
            wb_status,
            supply_id
        FROM penalties_mv
        """

        where_conditions = []
        params = []

        if date_from:
            where_conditions.append(f"date >= ${len(params) + 1} ")
            params.append(date_from)

        if date_to:
            where_conditions.append(f"date <= ${len(params) + 1} ")
            params.append(date_to)

        if where_conditions:
            query += "WHERE " + "AND ".join(where_conditions)

        query += "ORDER BY date DESC "

        if limit:
            query += f"LIMIT ${len(params) + 1}"
            params.append(limit)

        if offset:
            query += f" OFFSET ${len(params) + 1};"
            params.append(offset)

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
        except UndefinedTableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table or materialized view not found",
            )

        penalties_by_date = {}

        for row in rows:
            data = dict(row)
            penalties_date = data.pop("penalty_date")

            if not penalties_date in penalties_by_date:
                penalties_by_date[penalties_date] = list()

            penalties_by_date[penalties_date].append(PenaltyDetails(**data))

        return [DaylyPenaltiesReport(
            penalties_date=date,
            penalties=penalties
        ) for date, penalties in penalties_by_date.items()]
