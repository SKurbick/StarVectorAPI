from asyncpg import Pool
from fastapi import Depends, Request

from app.repository.financial_reporting import FinancialReportingRepository
from app.service.financial_reporting import FinancialReportingService


def get_pool(request: Request) -> Pool:
    return request.app.state.pool

def get_financial_reporting_repository(
        pool: Pool = Depends(get_pool)
) -> FinancialReportingRepository:
    return FinancialReportingRepository(pool)

def get_financial_reporting_service(
        repository: FinancialReportingRepository = Depends(get_financial_reporting_repository)
) -> FinancialReportingService:
    return FinancialReportingService(repository)