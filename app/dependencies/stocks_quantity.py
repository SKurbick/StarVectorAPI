from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.stocks_quantity import StocksQuantityRepository
from app.service.stocks_quantity import StocksQuantityService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_stocks_quantity_repository(pool: Pool = Depends(get_pool)) -> StocksQuantityRepository:
    return StocksQuantityRepository(pool)


def get_stocks_quantity_service(repository: StocksQuantityRepository = Depends(get_stocks_quantity_repository)) -> StocksQuantityService:
    return StocksQuantityService(repository)
