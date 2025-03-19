from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.percent_by_tax import PercentByTaxRepository
from app.service.percent_by_tax import PercentByTaxService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_percent_by_tax_repository(pool: Pool = Depends(get_pool)) -> PercentByTaxRepository:
    return PercentByTaxRepository(pool)


def get_percent_by_tax_service(repository: PercentByTaxRepository = Depends(get_percent_by_tax_repository)) -> PercentByTaxService:
    return PercentByTaxService(repository)
