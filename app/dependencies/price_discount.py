from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.price_discount import PriceDiscountRepository
from app.service.price_discount import PriceDiscountService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_price_discount_repository(pool: Pool = Depends(get_pool)) -> PriceDiscountRepository:
    return PriceDiscountRepository(pool)


def get_price_discount_service(repository: PriceDiscountRepository = Depends(get_price_discount_repository)) -> PriceDiscountService:
    return PriceDiscountService(repository)
