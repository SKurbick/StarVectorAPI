from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.service.close_card import CloseCardService


def get_close_card_service(
    pool: Pool = Depends(get_pool),
) -> CloseCardService:
    return CloseCardService(pool=pool)
