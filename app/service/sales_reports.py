import asyncio
from datetime import date, timedelta
import logging
from typing import AsyncGenerator, Literal

import aiohttp
import asyncpg

from app.config.settings import get_wb_tokens
from app.domain.models import (
    WeeklyFinReportsAggregated, 
    PeriodRequestModel,
    SalesReportResultStats,
    SalesReportResultStatsByAccount,
)
from app.infrastructure.API.wildberries.finance.schemes.sales_report import SalesReportRow
from app.infrastructure.API.wildberries.finance.wb_sales_reports import SalesReportsWBAPI
from app.repository.sales_reports import SalesReportRepository


FETCH_REPORT_LOCK = asyncio.Lock()
WEEKLY_FINN_REPORT_MAIN_TABLE = "fin_reports_full"
DAILY_FINN_REPORT_MAIN_TABLE = "daily_fin_reports_full"


class SalesReportsService:
    """
    Сервис для работы с финансовыми отчетами о продажах по реализации.
    """
    BATCH_SIZE_LIMIT = 30000

    def __init__(
            self, 
            session: aiohttp.ClientSession,
            sales_report_repo: SalesReportRepository,
    ):
        self._session = session
        self._sales_report_repo = sales_report_repo
        logging.debug(f"{SalesReportsService.__name__} инициализирован.")

    async def get_sales_reports_aggregated(
        self,
        period: PeriodRequestModel,
        number_of_last_weeks: int | None = None,
    ) -> list[WeeklyFinReportsAggregated]:
        """
        Получить аггрегированные данные по отчетам продаж за период.
        """
        return await self._sales_report_repo.get_sales_reports_aggregated(period, number_of_last_weeks)

    async def update_daily_fin_reports_agg(self, number_of_last_days: int = 1):
        """
        Обновить таблицу для сводных данных.
        """
        return await self._sales_report_repo.update_daily_fin_reports_agg(number_of_last_days)

    async def update_daily_fin_reports_deduction(self, number_of_last_days: int = 1):
        """
        Обновить таблицу с удержаниями из ежедневных финансовых отчетов."
        """
        return await self._sales_report_repo.update_daily_fin_reports_deductions(number_of_last_days)

    @staticmethod
    def validate_dates(
        period: Literal["daily", "weekly"],
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[date, date]:
        logging.debug(f"Валидируем диапазон дат для отчетов: [{period=}|date_from={str(date_from)}|date_to={str(date_to)}]...")
        today = date.today()

        if period == 'daily':
            yesterday = today - timedelta(days=1)

            date_from = min(date_from, yesterday) if date_from is not None else yesterday
            date_to = max(date_to, date_from) if date_to is not None else date_from
        elif period == 'weekly':
            last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)

            date_to = min(date_to, last_sunday) if date_to is not None else last_sunday
            sunday_date_to = date_to - timedelta(days=(date_to.weekday() + 1) % 7)

            date_from = min(date_from, sunday_date_to) if date_from is not None else sunday_date_to
            monday_date_from = date_from - timedelta(days=date_from.weekday())

            date_from = monday_date_from
            date_to = sunday_date_to

        logging.debug(f"Возвращаем диапазон дат для отчетов: [{period=}|date_from={str(date_from)}|date_to={str(date_to)}]...")
        return date_from, date_to

    async def fetch_sales_reports(
            self,
            period: Literal["daily", "weekly"],
            date_from: date | None = None,
            date_to: date | None = None,
    ) -> SalesReportResultStats:
        """
        Получить отчеты о продажах по реализации для всех аккаунтов.
        """
        date_from, date_to = self.validate_dates(period, date_from, date_to)
        async with FETCH_REPORT_LOCK:
            try:
                logging.info(f"Старт получения отчетов со всех аккаунтов. [date_from={str(date_from)}|date_to={str(date_to)}|{period=}]")
                async with self._sales_report_repo.transaction() as conn:
                    result = await self._execute_fetch_sales_reports_from_all_accounts(
                        date_from=date_from,
                        date_to=date_to,
                        period=period,
                        db_conn=conn,
                    )
                    return result
            except Exception as e:
                logging.exception(f"Необработанное исключение во обновления отчетов - [date_from={str(date_from)}|date_to={str(date_to)}|{period=}] - {e=}")
                raise

        logging.info(f"Получение отчетов со всех аккаунтов завершено. [date_from={str(date_from)}|date_to={str(date_to)}|{period=}]")
    
    async def _execute_fetch_sales_reports_from_all_accounts(
            self,
            date_from: date,
            date_to: date,
            period: Literal["daily", "weekly"],
            db_conn: asyncpg.Connection,
    ) -> SalesReportResultStats:
        # получить аккаунты
        all_accounts = await self._get_all_accounts()

        # получить имя временной таблицы для сохранения данных
        main_table_name, tmp_table_name = self._get_table_names(period=period)
        # создать временную таблицу
        await self._sales_report_repo.create_temp_table(
            conn=db_conn,
            main_table_name=main_table_name,
            tmp_table_name=tmp_table_name,
        )
        logging.debug(f"Создана временная таблица '{tmp_table_name}' на основе '{main_table_name}'")
        batch_insert_lock = asyncio.Lock()
        # приступить к выполнению по аккаунтам

        target_accounts = all_accounts
        valid_results: list[SalesReportResultStatsByAccount] = []
        exceptions = None

        attempt_count = 5
        for attempt in range(1, attempt_count + 1, 1):
            logging.debug(f"Получаем отчеты с аккаунтов: [{attempt=}|{target_accounts=}]")
            tasks = [asyncio.create_task(self.procces_account(
                account=account,
                date_from=date_from,
                date_to=date_to,
                period=period,
                db_conn=db_conn,
                temp_table=tmp_table_name,
                batch_insert_lock=batch_insert_lock,
            )) for account in target_accounts]

        # ожидаем выгрузки данных со всех отчетов во временную таблицу
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logging.debug(f"Обработка аккаунтов завершена. {attempt=}|{target_accounts=}")
            current_exceptions = []
            for acc, res in zip(all_accounts, results):
                if isinstance(res, Exception):
                    logging.exception(f"Обработка аккаунта '{acc}' завершена ошибкой: {res}")
                    current_exceptions.append({
                        "account": acc,
                        "error": str(res),
                    })
                    continue

                valid_results.append(res)

            exceptions = current_exceptions 

            if not current_exceptions:
                break

            if attempt < attempt_count:
                target_accounts = [exp["account"] for exp in current_exceptions]

        for valid_res in valid_results:
            logging.info(f"Выполнено успешно: account={valid_res.account}|rows_count={valid_res.report_rows_count}")

        if len(valid_results) != len(all_accounts):
            raise RuntimeError(f"Во время обработки аккаунтов не все были завершены корректно. errors={exceptions}")

        logging.debug(f"Удаляем данные из {main_table_name} за период: {str(date_from)}-{str(date_to)}...")
        await self._sales_report_repo.clean_data_from_table_by_period(
            conn=db_conn,
            table_name=main_table_name,
            date_from=date_from,
            date_to=date_to if period == "weekly" else None,
        )
        logging.debug(f"Сохраняем данные в {main_table_name} из {tmp_table_name} за период: {str(date_from)}-{str(date_to)}...")
        await self._sales_report_repo.merge_tmp_to_main_table(
            conn=db_conn, 
            main_table_name=main_table_name,
            tmp_table_name=tmp_table_name,
        )

        return SalesReportResultStats(
            date_from=date_from,
            date_to=date_to,
            period=period,
            accounts_stats=valid_results,
        )

    @staticmethod
    def _get_table_names(period: Literal["daily", "weekly"]) -> tuple[str, str]:
        """
        Получить имя для основной и временной таблиц.
        """
        tmp_table = f"tmp_{period}_finn_report"
        main_table = DAILY_FINN_REPORT_MAIN_TABLE if period == "daily" else WEEKLY_FINN_REPORT_MAIN_TABLE

        return main_table, tmp_table

    @staticmethod
    async def _get_all_accounts():
        """
        Получить все аккаунты из файла с токенами.
        """
        tokens = await get_wb_tokens()
        return tuple(item.capitalize() for item in tokens.keys())

    async def procces_account(
            self,
            account: str,
            date_from: date,
            date_to: date,
            period: Literal["daily", "weekly"],
            db_conn: asyncpg.Connection,
            temp_table: str,
            batch_insert_lock: asyncio.Lock,
    ) -> SalesReportResultStatsByAccount:
        """
        Выполнить загрузку и обработку отчетов по реализации для аккаунта.
        """
        sales_report_meta = f"[{account}|date_from={str(date_from)}|date_to={str(date_to)}|{period=}]"
        logging.info(f"Старт загрузки отчетов по реализации: {sales_report_meta}")
        counter_batch_size = 0

        async for batch in self._sales_reports_generator(
            account=account,
            date_from=date_from,
            date_to=date_to,
            period=period,
        ):
            counter_batch_size += len(batch)
            logging.debug(f"Получен батч к сохранению: {sales_report_meta} - count={len(batch)}")
            # сохранить во временную таблицу
            async with batch_insert_lock:
                await self._sales_report_repo.insert_batch(
                    conn=db_conn,
                    table_name=temp_table,
                    records=batch
                )

            logging.debug(f"Батч сохраненен: {sales_report_meta}, batch_size={len(batch)}")
        logging.info(f"Загрузки отчетов по реализации завершена: {sales_report_meta}|{counter_batch_size=}")
        return SalesReportResultStatsByAccount(
            account=account, 
            report_rows_count=counter_batch_size,
        )

    async def _sales_reports_generator(
            self,
            account: str,
            date_from: date,
            date_to: date,
            period: Literal["daily", "weekly"],
    ) -> AsyncGenerator[list[SalesReportRow], None]:
        """
        Генератор для получения строк отчетов батчами за период.
        """
        wb_client = SalesReportsWBAPI(
            session=self._session,
            account_name=account,
        )
        last_rrd_id = 0

        batch_meta_base = f"{wb_client.account_name}|date_from={str(date_from)}|date_to={str(date_to)}|{period=}"
        logging.info(f"Начинаем получение батчей строк отчетов: [{batch_meta_base}]")
        batch_meta_last_rrd_id = f"{last_rrd_id=}"
        has_data = True

        while has_data:
            batch_meta_full = f"[{batch_meta_base}|{batch_meta_last_rrd_id}]"
            logging.debug(f"Получаем батч строк отчетов о продажах: {batch_meta_full}")
            rows = await wb_client._get_sales_reports(
                date_from=date_from,
                date_to=date_to,
                limit=self.BATCH_SIZE_LIMIT,
                last_rrd_id=last_rrd_id,
                period=period,
            )

            if not rows:
                logging.debug(f"Батч строк отчетов пустой: {batch_meta_full}")
                break
            logging.debug(f"Получен батч строк отчетов: {batch_meta_full}, len={len(rows)}")
            if len(rows) < self.BATCH_SIZE_LIMIT:
                logging.debug(f"Возвращаем последний батч строк отчетов: {batch_meta_full}")
                has_data = False

            yield rows
            last_rrd_id = rows[-1].rrd_id
            batch_meta_last_rrd_id = f"{last_rrd_id=}"

        logging.info(f"Завершили итерацию по батчам строк отчетов: [{batch_meta_base}]")
