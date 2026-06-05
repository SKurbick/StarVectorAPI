from datetime import date, timedelta
from typing import Literal

from app.infrastructure.API.wildberries.base.client import HTTPMethod, WBClientError

from .base import FinanceWBAPI
from .schemes.sales_report import SalesReportRow


DEFAULT_LIMIT_FINANCE_REPORT_ROWS = 30000
MAX_LIMIT_FINANCE_REPORT_ROWS = 100000


class SalesReportsWBAPI(FinanceWBAPI):
    """
    API-клиент финансовых отчетов реализации WB.
    """

    WB_SALES_REPORTS_DATAILED = "/finance/v1/sales-reports/detailed"

    async def get_daily_sales_reports(
            self,
            date_from: date | None = None,
            date_to: date | None = None,
            limit: int = DEFAULT_LIMIT_FINANCE_REPORT_ROWS,
            last_rrd_id: int = 0
    ) -> list[SalesReportRow]:
        """
        Получить детализации к ежедневным отчетам реализации за указанный период.
        """
        yesterday = date.today() - timedelta(days=1)

        return await self._get_sales_reports(
            date_from=date_from or yesterday,
            date_to=date_to or yesterday,
            limit=limit,
            last_rrd_id=last_rrd_id,
            period="daily",
        )

    async def get_weekly_sales_reports(
            self,
            date_from: date | None = None,
            date_to: date | None = None,
            limit: int = DEFAULT_LIMIT_FINANCE_REPORT_ROWS,
            last_rrd_id: int = 0
    ) -> list[SalesReportRow]:
        """
        Получить детализации к еженедельным отчетам реализации за указанный период.
        """
        today = date.today()
        last_sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        return await self._get_sales_reports(
            date_from=date_from or last_sunday,
            date_to=date_to or last_sunday,
            limit=limit,
            last_rrd_id=last_rrd_id,
        )

    async def _get_sales_reports(
            self, 
            date_from: date,
            date_to: date,
            limit: int = DEFAULT_LIMIT_FINANCE_REPORT_ROWS,
            last_rrd_id: int = 0,
            period: Literal["daily", "weekly"] = "weekly",
    ) -> list[SalesReportRow]:
        """
        Получить строки финансовых отчетов о продажах по реализации.
        """
        if not date_from or not isinstance(date_from, date):
            raise ValueError(f"Некорректное значение поля {date_from=}, type={type(date_from)}")
        
        if not date_to or not isinstance(date_to, date):
            raise ValueError(f"Некорректное значение поля {date_to=}, type={type(date_to)}")

        limit = min(max(1, limit), MAX_LIMIT_FINANCE_REPORT_ROWS)

        payload = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
            "limit": limit,
            "rrdId": last_rrd_id,
            "period": period,
        }

        try:
            rows = await self._make_request(
                endpoint=self.WB_SALES_REPORTS_DATAILED,
                method=HTTPMethod.POST,
                payload=payload,
            )
        except WBClientError as e:
            if e.status_code == 204:
                return []

            raise

        return [SalesReportRow(**row, account=self.account_name) for row in rows]
