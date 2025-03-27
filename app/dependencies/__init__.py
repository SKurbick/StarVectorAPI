from .card_data import get_card_data_repository, get_card_data_service
from .orders_revenues import get_orders_revenues_service, get_orders_revenues_repository
from .article import get_article_service, get_article_repository
from .price_discount import get_price_discount_service, get_price_discount_repository
from .unit_economics import get_unit_economics_service, get_unit_economics_repository
from .net_profit import get_net_profit_service, get_net_profit_repository
from .percent_by_tax import get_percent_by_tax_service, get_percent_by_tax_repository
from .stocks_quantity import get_stocks_quantity_service, get_stocks_quantity_repository
from .turnover import get_turnover_service, get_turnover_repository

__all__ = [
    "get_article_repository",
    "get_article_service",
    "get_orders_revenues_repository",
    "get_orders_revenues_service",
    "get_card_data_repository",
    "get_card_data_service",
    "get_price_discount_repository",
    "get_price_discount_service",
    "get_unit_economics_service",
    "get_unit_economics_repository",
    "get_net_profit_service",
    "get_net_profit_repository",
    "get_percent_by_tax_service",
    "get_percent_by_tax_repository",
    "get_stocks_quantity_service",
    "get_stocks_quantity_repository",
    "get_turnover_service",
    "get_turnover_repository",
]
