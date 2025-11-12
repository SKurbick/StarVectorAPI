from fastapi import Depends
from asyncpg import Pool

from app.repository.card_status import CardStatusRepository
from app.service.card_status import CardStatusService

from app.dependencies.database import get_pool


def get_card_status_repository(pool: Pool = Depends(get_pool)) -> CardStatusRepository:
    return CardStatusRepository(pool)


def get_card_status_service(
    repository: CardStatusRepository = Depends(get_card_status_repository)
) -> CardStatusService:
    return CardStatusService(repository)
