from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.penalties import PenaltyRepository
from app.service.penalties import PenaltyService


def get_penalty_repository(pool: Pool = Depends(get_pool)) -> PenaltyRepository:
    return PenaltyRepository(pool)


def get_penalty_service(repository: PenaltyRepository = Depends(get_penalty_repository)) -> PenaltyService:
    return PenaltyService(repository)
