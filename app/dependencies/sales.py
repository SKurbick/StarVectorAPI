from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.sales import SaleRepository
from app.service.sales import SaleService


def get_sale_repository(pool: Pool = Depends(get_pool)) -> SaleRepository:
    return SaleRepository(pool)


def get_sale_service(repository: SaleRepository = Depends(get_sale_repository)) -> SaleService:
    return SaleService(repository)
