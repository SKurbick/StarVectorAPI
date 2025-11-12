from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.service.open_card import OpenCardService


def get_open_card_service(
    pool: Pool = Depends(get_pool),
) -> OpenCardService:
    return OpenCardService(pool=pool)
