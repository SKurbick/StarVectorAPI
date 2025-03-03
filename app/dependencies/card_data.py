from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.card_data import CardDataRepository
from app.service.card_data import CardDataService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_card_data_repository(pool: Pool = Depends(get_pool)) -> CardDataRepository:
    return CardDataRepository(pool)


def get_card_data_service(repository: CardDataRepository = Depends(get_card_data_repository)) -> CardDataService:
    return CardDataService(repository)
