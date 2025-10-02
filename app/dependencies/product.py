from typing import Annotated

from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.product import ProductRepository
from app.service.product import ProductService


def get_product_repository(
    pool: Annotated[Pool, Depends(get_pool)]
) -> ProductRepository:
    return ProductRepository(pool)


def get_product_service(
    reposytory: Annotated[ProductRepository, Depends(get_product_repository)]
) -> ProductService:
    return ProductService(reposytory)
