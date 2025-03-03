from .card_data import get_card_data_repository, get_card_data_service
from .orders_revenues import get_orders_revenues_service, get_orders_revenues_repository
from .article import get_article_service, get_article_repository

from .price_discount import get_price_discount_service, get_price_discount_repository

__all__ = [
    "get_article_repository",
    "get_article_service",
    "get_orders_revenues_repository",
    "get_orders_revenues_service",
    "get_card_data_repository",
    "get_card_data_service",
    "get_price_discount_repository",
    "get_price_discount_service"
]
