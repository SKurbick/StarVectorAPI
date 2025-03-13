from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.unit_economics import UnitEconomicsRepository
from app.service.unit_economics import UnitEconomicsService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_unit_economics_repository(pool: Pool = Depends(get_pool)) -> UnitEconomicsRepository:
    return UnitEconomicsRepository(pool)


def get_unit_economics_service(repository: UnitEconomicsRepository = Depends(get_unit_economics_repository)) -> UnitEconomicsService:
    return UnitEconomicsService(repository)
