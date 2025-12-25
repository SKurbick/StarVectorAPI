from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.sales import SaleRepository
from app.repository.sales_management import SalesManagementRepository
from app.service.sales import SaleService
from app.service.sales_management import SalesManagementService


def get_sales_management_repository(pool: Pool = Depends(get_pool)) -> SalesManagementRepository:
    return SalesManagementRepository(pool)


def get_sales_management_service(repository: SaleRepository = Depends(get_sales_management_repository)) -> SalesManagementService:
    return SalesManagementService(repository)
