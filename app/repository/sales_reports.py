from contextlib import asynccontextmanager
from datetime import date
from typing import Iterable, AsyncGenerator
import logging

import asyncpg

from app.domain.models import WeeklyFinReportsAggregated, PeriodRequestModel, FinReportDeduction
from app.infrastructure.API.wildberries.finance.schemes.sales_report import SalesReportRow


class SalesReportRepository:
    """
    Репозиторий для финансовых отчётов по реализации товаров на WB.
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool        
        self._columns: list[str] | None = None
        self._columns_sql: str | None = None
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Получить соединение с БД в рамках транзакции.
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                logging.debug(f"Открыта транзакция в {SalesReportRepository.__name__}")
                yield conn
                logging.debug(f"Закрыта транзакция в {SalesReportRepository.__name__}")

    async def get_sales_reports_aggregated(
        self,
        period: PeriodRequestModel,
        number_of_last_weeks: int | None = None,
    ) -> list[WeeklyFinReportsAggregated]:
        """
        Получить аггрегированные данные по отчетам продаж.
        """
        main_query = """
        SELECT
            fram.date_to,
            fram."Комиссия ВБ" AS wb_commission,
            fram."Комиссия ВБ pct" AS wb_commission_percentage,
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
            fram."Наша доля до вычета себестоимости" AS our_share_before_cost,
            fram."ВП после ВБ" AS vp_after_wb,
            fram."ВП после ВБ pct" AS vp_after_wb_percentage,
            fdm.grouped_bonus_type_name,
            fdm.total_deduction AS deduction
        FROM ({subquery}) fram
        LEFT JOIN fin_deductions_mv fdm
        ON fram.date_to = fdm.date_to
        ORDER BY fram.date_to DESC;
        """

        subquery = """
            SELECT *
            FROM weekly_fin_reports_mv
            WHERE date_to BETWEEN $1 AND $2
        """

        params = [period.date_from, period.date_to]

        if number_of_last_weeks:
            subquery += f" LIMIT $3"
            params.append(number_of_last_weeks)

        full_query = main_query.format(subquery=subquery)

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(full_query, *params)
        except asyncpg.UndefinedTableError:
            raise RuntimeError(
                "Таблица или мат.представление не найдено.",
            )

        reports = {}

        for row in rows:
            report_date_to = row["date_to"]

            if not reports.get(report_date_to):
                reports[report_date_to] = dict(
                    date_to=row["date_to"],
                    wb_commission=row["wb_commission"],
                    wb_commission_percentage=row["wb_commission_percentage"],
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
                    our_share_before_cost=row["our_share_before_cost"],
                    vp_after_wb=row["vp_after_wb"],
                    vp_after_wb_percentage=row["vp_after_wb_percentage"],
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

    async def _ensure_columns_loaded(self, conn: asyncpg.Connection, main_table: str) -> None:
        """
        Загрузить актуальный список колонок из основной таблицы БД.
        """
        if self._columns is not None:
            return

        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position ASC
        """
        rows = await conn.fetch(query, main_table)
        
        if not rows:
            raise ValueError(f"Таблица '{main_table}' не найдена или не имеет колонок.")

        print(self._columns)
        self._columns = [row["column_name"] for row in rows]
        self._columns_sql = ", ".join(self._columns)

    async def create_temp_table(
            self, 
            conn: asyncpg.Connection, 
            main_table_name: str, 
            tmp_table_name: str
    ) -> str:
        """
        Создаёт временную таблицу с той же структурой, что и основная.
        """
        if not main_table_name.strip():
            raise ValueError(f"Передано пустое значение названия основной таблицы.")

        if not tmp_table_name.strip():
            raise ValueError(f"Передано пустое значение для названия временной таблицы.")

        await self._ensure_columns_loaded(conn, main_table_name)

        query = f"""
            CREATE TEMPORARY TABLE {tmp_table_name}
            ON COMMIT DROP
            AS SELECT * FROM {main_table_name}
            WITH NO DATA;
        """

        await conn.execute(query)
        return tmp_table_name

    async def insert_batch(
            self, 
            conn: asyncpg.Connection, 
            table_name: str, 
            records: Iterable[SalesReportRow]
    ) -> int:
        """
        Пакетная вставка данных в таблицу через COPY протокол PostgreSQL.
        """
        if not records:
            return

        tuples = [tuple(getattr(record, col, None) for col in self._columns) for record in records]

        result = await conn.copy_records_to_table(
            table_name=table_name,
            records=tuples,
            columns=self._columns
        )
        logging.debug(f"Выполнена вставка в БД: [{table_name=}|records-in={len(tuples)}|{result}]")
        return len(tuples)

    async def clean_data_from_table_by_period(
            self,
            conn: asyncpg.Connection,
            table_name: str,
            date_from: date,
            date_to: date | None = None,
    ) -> None:
        """
        Удалить данные из таблицы за период.
        """

        params = [date_from]

        delete_query = f"""
            DELETE FROM {table_name}
            WHERE date_from = $1
        """

        if date_to is not None:
            delete_query += " AND date_to = $2"
            params.append(date_to)

        await conn.execute(delete_query, *params)

    async def merge_tmp_to_main_table(
            self,
            conn: asyncpg.Connection,
            main_table_name: str,
            tmp_table_name: str,
    ) -> None:
        """
        Залить данные из временной таблицы в основную.
        """
        update_set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in self._columns])

        query = f"""
            INSERT INTO {main_table_name} ({self._columns_sql})
            SELECT DISTINCT ON (realizationreport_id, rrd_id) {self._columns_sql}
            FROM {tmp_table_name}
            ON CONFLICT (realizationreport_id, rrd_id) 
            DO UPDATE SET {update_set_clause};
        """

        await conn.execute(query)

    async def update_daily_fin_reports_agg(self, number_of_last_days: int = 1) -> None:
        """
        Обновить данные в таблице daily_fin_reports_agg за предыдущий день.
        """
        if not isinstance(number_of_last_days, int):
            raise ValueError("'number_of_last_days' - ожидаем тип параметра 'int'.")

        str_interval = f"{number_of_last_days} day"

        latest_purchase_price_cte = f"""
            latest_purchase_price AS (
                SELECT 
                    cp.local_vendor_code, 
                    a.nm_id,
                    ROUND(AVG(cp.purchase_price)) AS price_per_item,
                    cp.date 
                FROM cost_price cp 
                LEFT JOIN article a 
                    ON a.local_vendor_code = cp.local_vendor_code 
                WHERE cp.date BETWEEN (CURRENT_DATE - INTERVAL '{str_interval}') AND (CURRENT_DATE - INTERVAL '1 day')
                GROUP BY cp.date, cp.local_vendor_code, a.nm_id
            )
        """

        purchase_cost_by_date_cte = f"""
            purchase_cost_by_date AS (
                     SELECT
                        f_1.date_from,
                        f_1.account,
                        SUM(
                            CASE
                                WHEN f_1.supplier_oper_name = 'Продажа'
                                THEN f_1.quantity * lpp.price_per_item
                                ELSE 0
                            END
                        ) AS purchase_cost_sales,
                        SUM(
                            CASE
                                WHEN f_1.supplier_oper_name = 'Возврат'
                                THEN f_1.quantity * lpp.price_per_item
                                ELSE 0
                            END
                        ) AS purchase_cost_returns
                    FROM daily_fin_reports_full f_1
                    LEFT JOIN latest_purchase_price lpp
                        ON f_1.nm_id = lpp.nm_id 
                        AND f_1.date_from = lpp.date
                    WHERE f_1.supplier_oper_name IN ('Продажа', 'Возврат')
                        AND f_1.date_from BETWEEN (CURRENT_DATE - INTERVAL '{str_interval}') AND (CURRENT_DATE - INTERVAL '1 day')
                    GROUP BY f_1.date_from, f_1.account
            )
        """

        financials_cte = f"""
            financials AS (
                SELECT
                f.date_from,
                f.account,
                SUM(CASE WHEN f.supplier_oper_name = 'Продажа' THEN f.retail_price_withdisc_rub ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Возврат' THEN f.retail_price_withdisc_rub ELSE 0 END)
                - (
                SUM(CASE WHEN f.supplier_oper_name = 'Продажа' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Коррекция продаж' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Добровольная компенсация при возврате' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция возвратов' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Возврат' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Компенсация ущерба' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Корректировка эквайринга' THEN f.ppvz_for_pay ELSE 0 END)
                ) AS wb_commission,
                SUM(CASE WHEN f.supplier_oper_name = 'Продажа' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Коррекция продаж' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Добровольная компенсация при возврате' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция возвратов' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Возврат' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Компенсация ущерба' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Корректировка эквайринга' THEN f.ppvz_for_pay ELSE 0 END) AS payout,
                SUM(CASE WHEN f.supplier_oper_name = 'Логистика' THEN f.delivery_rub ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция логистики' THEN f.delivery_rub ELSE 0 END) AS logistics,
                SUM(CASE WHEN f.supplier_oper_name = 'Продажа' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Коррекция продаж' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Добровольная компенсация при возврате' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция возвратов' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Возврат' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Компенсация ущерба' THEN f.ppvz_for_pay ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Корректировка эквайринга' THEN f.ppvz_for_pay ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Штраф' THEN f.penalty ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Удержание' THEN f.deduction ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Платная приемка' THEN f.acceptance ELSE 0 END)
                - (
                SUM(CASE WHEN f.supplier_oper_name = 'Логистика' THEN f.delivery_rub ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция логистики' THEN f.delivery_rub ELSE 0 END)
                ) AS total_to_pay,
                SUM(CASE WHEN f.supplier_oper_name = 'Продажа' THEN f.retail_price_withdisc_rub ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Возврат' THEN f.retail_price_withdisc_rub ELSE 0 END)
                - SUM(CASE WHEN f.supplier_oper_name = 'Коррекция возвратов' THEN f.retail_price_withdisc_rub ELSE 0 END)
                + SUM(CASE WHEN f.supplier_oper_name = 'Коррекция продаж' THEN f.retail_price_withdisc_rub ELSE 0 END) AS revenue,
                SUM(f.retail_price_withdisc_rub) AS retail_price_disc,
                SUM(f.penalty) AS penalties,
                SUM(f.storage_fee) AS storage_fee,
                SUM(f.deduction) AS deductions,
                SUM(f.acceptance) AS paid_acceptance,
                SUM(f.acquiring_fee) AS acquiring_fee,
                SUM(CASE WHEN f.bonus_type_name ILIKE '%кредит%' THEN f.deduction ELSE 0 END) AS credit_transfers,
                SUM(CASE WHEN f.bonus_type_name = 'К клиенту при отмене' THEN f.delivery_rub ELSE 0 END) AS to_client_cancel,
                SUM(CASE WHEN f.bonus_type_name = 'От клиента при отмене' THEN f.delivery_rub ELSE 0 END) AS from_client_cancel,
                SUM(CASE WHEN f.bonus_type_name = 'От клиента при возврате' THEN f.delivery_rub ELSE 0 END) AS from_client_return,
                SUM(CASE WHEN f.bonus_type_name = 'К клиенту при продаже' THEN f.delivery_rub ELSE 0 END) AS to_client_sale
            FROM daily_fin_reports_full f
            WHERE f.date_from BETWEEN (CURRENT_DATE - INTERVAL '{str_interval}') AND (CURRENT_DATE - INTERVAL '1 day')
            GROUP BY f.date_from, f.account
            )
        """

        all_cte_query = f"WITH {latest_purchase_price_cte},{purchase_cost_by_date_cte},{financials_cte} "
        full_query = all_cte_query + """
            INSERT INTO daily_fin_reports_agg
            SELECT
                f.date_from,
                f.wb_commission,
                CASE WHEN f.revenue <> 0 THEN ROUND(f.wb_commission / f.revenue, 4) * 100 ELSE 0 END AS wb_commission_pct,
                f.payout,
                f.logistics,
                f.total_to_pay,
                f.revenue,
                f.retail_price_disc,
                f.penalties,
                f.storage_fee,
                f.deductions,
                f.paid_acceptance,
                f.credit_transfers,
                f.to_client_cancel,
                f.from_client_cancel,
                f.from_client_return,
                f.to_client_sale,
                COALESCE(p.purchase_cost_sales, 0) AS purchase_cost_sales,
                COALESCE(p.purchase_cost_returns, 0) AS purchase_cost_returns,
                COALESCE(p.purchase_cost_sales, 0) - COALESCE(p.purchase_cost_returns, 0) AS purchase_cost_total,
                CASE WHEN f.revenue <> 0 THEN ROUND(f.total_to_pay / f.revenue, 4) * 100 ELSE 0 END AS margin_before_cost_pct,
                f.total_to_pay - (COALESCE(p.purchase_cost_sales, 0) - COALESCE(p.purchase_cost_returns, 0)) + f.credit_transfers AS gp_after_wb,
                CASE
                WHEN f.revenue <> 0 THEN
                    ROUND(
                        (f.total_to_pay
                        - (COALESCE(p.purchase_cost_sales, 0) - COALESCE(p.purchase_cost_returns, 0))
                        + f.credit_transfers
                        ) / f.revenue,
                    4) * 100
                ELSE 0
                END AS gp_after_wb_pct,
                f.account,
                f.acquiring_fee
            FROM financials f
            LEFT JOIN purchase_cost_by_date p
                ON f.date_from = p.date_from
                AND f.account = p.account
            ON CONFLICT (date_from, account) DO UPDATE SET
                wb_commission = EXCLUDED.wb_commission,
                wb_commission_pct = EXCLUDED.wb_commission_pct,
                payout = EXCLUDED.payout,
                logistics = EXCLUDED.logistics,
                total_to_pay = EXCLUDED.total_to_pay,
                revenue = EXCLUDED.revenue,
                retail_price_disc = EXCLUDED.retail_price_disc,
                penalties = EXCLUDED.penalties,
                storage_fee = EXCLUDED.storage_fee,
                deductions = EXCLUDED.deductions,
                paid_acceptance = EXCLUDED.paid_acceptance,
                credit_transfers = EXCLUDED.credit_transfers,
                to_client_cancel = EXCLUDED.to_client_cancel,
                from_client_cancel = EXCLUDED.from_client_cancel,
                from_client_return = EXCLUDED.from_client_return,
                to_client_sale = EXCLUDED.to_client_sale,
                purchase_cost_sales = EXCLUDED.purchase_cost_sales,
                purchase_cost_returns = EXCLUDED.purchase_cost_returns,
                purchase_cost_total = EXCLUDED.purchase_cost_total,
                margin_before_cost_pct = EXCLUDED.margin_before_cost_pct,
                gp_after_wb = EXCLUDED.gp_after_wb,
                acquiring_fee = EXCLUDED.acquiring_fee,
                gp_after_wb_pct = EXCLUDED.gp_after_wb_pct;
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(full_query)
        except asyncpg.PostgresError as e:
            raise Exception(f"Ошибка при обновлении таблицы daily_fin_reports_agg: {e}")

    async def update_daily_fin_reports_deductions(self, number_of_last_days: int = 1) -> None:
        """
        Обновить таблицу с удержаниями из ежедневных финансовых отчетов."
        """
        if not isinstance(number_of_last_days, int):
            raise ValueError("'number_of_last_days' - ожидаем тип параметра 'int'.")

        str_interval = f"{number_of_last_days} day"

        query = f"""
            INSERT INTO daily_fin_reports_deductions (
                date_from,
                grouped_bonus_type_name,
                total_deduction
            )
            SELECT
                date_from,
                CASE
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты по кредиту'::text
                    WHEN bonus_type_name ~~ 'Списание за отзыв%'::text THEN 'Списание за отзыв'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты процентов по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты процентов по кредиту'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты основного долга по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты основного долга по кредиту'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты комиссии по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты комиссии по кредиту'::text
                    WHEN bonus_type_name ~~ 'Услуги доставки транзитных поставок%'::text THEN 'Услуги доставки транзитных поставок'::text
                    WHEN bonus_type_name ~~ 'Акт утилизации товара(склад)%'::text THEN 'Акт утилизации товара(склад)'::text
                    WHEN bonus_type_name ~~ 'Оказание услуг «WB Продвижение»%'::text THEN 'Оказание услуг «WB Продвижение»'::text
                    WHEN bonus_type_name ~~ 'Предоставление услуг по подписке «Джем»%'::text THEN 'Предоставление услуг по подписке «Джем»'::text
                    ELSE bonus_type_name
                END AS grouped_bonus_type_name,
                SUM(deduction) AS total_deduction
            FROM daily_fin_reports_full
            WHERE supplier_oper_name = ANY (ARRAY['Удержание'::text, 'Удержания'::text])
            AND date_from BETWEEN (NOW() - INTERVAL '{str_interval}')::date AND (NOW() - INTERVAL '1 day')::date
            GROUP BY
                date_from,
                CASE
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты по кредиту'::text
                    WHEN bonus_type_name ~~ 'Списание за отзыв%'::text THEN 'Списание за отзыв'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты процентов по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты процентов по кредиту'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты основного долга по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты основного долга по кредиту'::text
                    WHEN bonus_type_name ~~ 'Перевод на баланс заёмщика для оплаты комиссии по кредиту%'::text THEN 'Перевод на баланс заёмщика для оплаты комиссии по кредиту'::text
                    WHEN bonus_type_name ~~ 'Услуги доставки транзитных поставок%'::text THEN 'Услуги доставки транзитных поставок'::text
                    WHEN bonus_type_name ~~ 'Акт утилизации товара(склад)%'::text THEN 'Акт утилизации товара(склад)'::text
                    WHEN bonus_type_name ~~ 'Оказание услуг «WB Продвижение»%'::text THEN 'Оказание услуг «WB Продвижение»'::text
                    WHEN bonus_type_name ~~ 'Предоставление услуг по подписке «Джем»%'::text THEN 'Предоставление услуг по подписке «Джем»'::text
                    ELSE bonus_type_name
                END
            ON CONFLICT (date_from, grouped_bonus_type_name) DO UPDATE SET
                total_deduction = EXCLUDED.total_deduction
        """

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(query)
        except asyncpg.PostgresError as e:
            raise Exception(f"Ошибка при обновлении таблицы daily_fin_reports_deductions: {e}")
