from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.card_data import CardDataRepository
from app.service.card_data import CardDataService

from app.repository.article import ArticleRepository
from app.service.article import ArticleService

from app.repository.orders_revenues import OrdersRevenuesRepository
from app.service.orders_revenues import OrdersRevenuesService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_card_data_repository(pool: Pool = Depends(get_pool)) -> CardDataRepository:
    return CardDataRepository(pool)


def get_card_data_service(repository: CardDataRepository = Depends(get_card_data_repository)) -> CardDataService:
    return CardDataService(repository)


def get_article_repository(pool: Pool = Depends(get_pool)) -> ArticleRepository:
    return ArticleRepository(pool)


def get_article_service(repository: ArticleRepository = Depends(get_article_repository)) -> ArticleService:
    return ArticleService(repository)


def get_orders_revenues_repository(pool: Pool = Depends(get_pool)) -> OrdersRevenuesRepository:
    return OrdersRevenuesRepository(pool)


def get_orders_revenues_service(repository: OrdersRevenuesRepository = Depends(get_orders_revenues_repository)) -> OrdersRevenuesService:
    return OrdersRevenuesService(repository)
