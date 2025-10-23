import asyncio
from datetime import date, timedelta
import logging
from typing import Optional
import os

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

    async def fetch_daily_fin_reports(self, date_from: Optional[str] = None, date_to: Optional[str] = None):
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        date_from = date_from or yesterday
        date_to = date_from or yesterday

        tokens = await get_wb_tokens()

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

                for result in results:
                    if isinstance(result, Exception):
                        logging.error(f"Ошибка при загрузке: {result}")

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

            async for raw_records in fetcher.fetch(date_from, date_to, limit=30000):
                if not raw_records:
                    logging.info(f"{account} | Нет данных за период {date_from}–{date_to}")

                count_saved_records = await self.repository.save_daily_fin_reports(raw_records, account)
                logging.info(f"{account} | Сохранено {count_saved_records} записей")

        except Exception as e:
            logging.exception(f"Критическая ошибка при обработке аккаунта {account}: {e}")
            raise Exception(e)
