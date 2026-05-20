from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.product import ProductRepository


def get_product_repository(
    pool: Pool = Depends(get_pool),
) -> ProductRepository:
    return ProductRepository(pool)
