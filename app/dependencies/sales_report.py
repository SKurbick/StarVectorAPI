from aiohttp import ClientSession
from asyncpg import Pool
from fastapi import Depends

from app.repository.sales_reports import SalesReportRepository
from app.service.sales_reports import SalesReportsService

from .database import get_pool
from .http_session import get_wb_http_session


def get_sales_reports_repo(pool: Pool = Depends(get_pool)) -> SalesReportRepository:
    return SalesReportRepository(pool=pool)


def get_sales_reports_service(
        session: ClientSession = Depends(get_wb_http_session),
        sales_report_repo: SalesReportRepository = Depends(get_sales_reports_repo),
) -> SalesReportsService:
    return SalesReportsService(
        session=session,
        sales_report_repo=sales_report_repo,
    )
