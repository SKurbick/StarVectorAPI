import asyncpg
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository.seller_account import SellerAccountRepository
from app.service.seller_account import SellerAccountService


def get_seller_account_repository(
    pool: asyncpg.Pool = Depends(get_pool)
) -> SellerAccountRepository:
    return SellerAccountRepository(pool)


def get_seller_account_service(
    repo: SellerAccountRepository = Depends(get_seller_account_repository)
) -> SellerAccountService:
    return SellerAccountService(repo)
