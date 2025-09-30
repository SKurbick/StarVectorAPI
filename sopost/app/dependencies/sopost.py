from typing import Annotated

from asyncpg import Pool
from fastapi import Depends

from dependencies.database import get_pool
from reposytory.sopost import SopostRepository
from service.sopost import SopostService


def get_sopost_repository(
    pool: Annotated[Pool, Depends(get_pool)]
) -> SopostRepository:
    return SopostRepository(pool)


def get_sopost_service(
    reposytory: Annotated[SopostRepository, Depends(get_sopost_repository)]
) -> SopostService:
    return SopostService(reposytory)
