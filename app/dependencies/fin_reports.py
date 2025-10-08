from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.fin_reports import FinReportsRepository
from app.service.fin_reports import FinReportsService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_fin_reports_repository(pool: Pool = Depends(get_pool)) -> FinReportsRepository:
    return FinReportsRepository(pool)


def get_fin_reports_service(repository: FinReportsRepository = Depends(get_fin_reports_repository)) -> FinReportsService:
    return FinReportsService(repository)
