import asyncio
from datetime import date, timedelta
import logging
from typing import Optional

import aiohttp
from fastapi import HTTPException

from app.config.settings import get_wb_tokens
from app.domain.models import WeeklyFinReportsAggregated, PeriodRequestModel
from app.infrastructure.WildberriesAPI.fin_reports import WBFinReportFetcher
from app.repository.fin_reports import FinReportsRepository


class FinReportsService:
    def __init__(
        self,
        repository: FinReportsRepository,
    ):
        self.repository = repository

    async def get_fin_reports_aggregated(
        self,
        period: PeriodRequestModel,
        number_of_last_weeks: Optional[int],
    ) -> list[WeeklyFinReportsAggregated]:
        return await self.repository.get_fin_reports_aggregated(period, number_of_last_weeks)

    async def fetch_daily_fin_reports(
        self, date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        empty_acc: bool = False
    ):
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        date_from = date_from or yesterday
        date_to = date_to or yesterday

        tokens = await get_wb_tokens()
        
        if not tokens:
            raise HTTPException(status_code=422, detail="No WB accounts configured")

        try:
            timeout = aiohttp.ClientTimeout(
                total=120, connect=30, sock_read=60, sock_connect=15
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                tasks = [
                    self._process_account_reports(
                        date_from=date_from, 
                        date_to=date_to, 
                        session=session,
                        account=account,
                        token=token)
                    for account, token in tokens.items()
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                safe_results = {}
                errors = []

                for (account, _), result in zip(tokens.items(), results):
                    if isinstance(result, Exception):
                        error_msg = f"Failed to process account '{account}': {result}"
                        logging.error(error_msg)
                        errors.append(error_msg)
                        safe_results[account] = None
                        continue

                    account_name, record_count = result
                    if not empty_acc and record_count == 0:
                        error_msg = f"Account '{account_name}' returned 0 records"
                        logging.error(error_msg)
                        errors.append(error_msg)
                        safe_results[account] = 0
                        continue

                    safe_results[account] = record_count

                if errors:
                    raise HTTPException(
                        status_code=422,
                        detail="One or more accounts failed: " + "; ".join(errors)
                    )

                return safe_results

        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"{e}"
            )

    async def _process_account_reports(
        self,
        date_from: str,
        date_to: str,
        session: aiohttp.ClientSession,
        account: str,
        token: str,
    ) -> list:
        """
        Получает, нормализует и валидирует финансовые отчёты для одного аккаунта.
        """
        try:
            fetcher = WBFinReportFetcher(
                account=account,
                api_token=token,
                session=session,
            )
            all_records_count = 0

            async for raw_records in fetcher.fetch(date_from, date_to, limit=30000):
                if not raw_records:
                    logging.info(f"{account} | Нет данных за период {date_from}–{date_to}")

                count_saved_records = await self.repository.save_daily_fin_reports(raw_records, account)
                logging.info(f"{account} | Сохранено {count_saved_records} записей")
                all_records_count += count_saved_records
            raise Exception(f"{account} test error")
            return (account, all_records_count)

        except Exception as e:
            logging.exception(f"Критическая ошибка при обработке аккаунта {account}: {e}")
            raise Exception(e)
