from typing import Annotated

from asyncpg import Pool
from fastapi import Depends

from app.service.banned_cards import BannedCardService
from app.repository.banned_cards import BannedCardRepository

from .database import get_pool


def get_banned_card_repo(
        pool: Annotated[Pool, Depends(get_pool)],
) -> BannedCardRepository:
    return BannedCardRepository(pool=pool)


def get_banned_card_service(
        banned_card_repo: Annotated[BannedCardRepository, Depends(get_banned_card_repo)],
) -> BannedCardService:
    return BannedCardService(
        banned_card_repo=banned_card_repo,
    )
