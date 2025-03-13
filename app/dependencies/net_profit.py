from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.net_profit import NetProfitRepository
from app.service.net_profit import NetProfitService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_net_profit_repository(pool: Pool = Depends(get_pool)) -> NetProfitRepository:
    return NetProfitRepository(pool)


def get_net_profit_service(repository: NetProfitRepository = Depends(get_net_profit_repository)) -> NetProfitService:
    return NetProfitService(repository)
