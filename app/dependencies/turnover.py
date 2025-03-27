from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.turnover import TurnoverRepository
from app.service.turnover import TurnoverService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_turnover_repository(pool: Pool = Depends(get_pool)) -> TurnoverRepository:
    return TurnoverRepository(pool)


def get_turnover_service(repository: TurnoverRepository = Depends(get_turnover_repository)) -> TurnoverService:
    return TurnoverService(repository)
