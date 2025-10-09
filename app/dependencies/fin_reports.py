from asyncpg import Pool
from fastapi import Depends

from app.repository.fin_reports import FinReportsRepository
from app.service.fin_reports import FinReportsService
from app.dependencies.database import get_pool


def get_fin_reports_repository(pool: Pool = Depends(get_pool)) -> FinReportsRepository:
    return FinReportsRepository(pool)


def get_fin_reports_service(repository: FinReportsRepository = Depends(get_fin_reports_repository)) -> FinReportsService:
    return FinReportsService(repository)
