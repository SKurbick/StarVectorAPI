from .card_data import router as card_data_router
from .article import router as article_router
from .price_discount import router as price_discount_router
from .orders_revenues import router as orders_revenues_router
from .unit_economics import router as unit_economics_router
from .net_profit import router as net_profit_router
from .percent_by_tax import router as percent_by_tax_router
from .stocks_quantity import router as stocks_quantity_router
from .favicon import router as favicon_router
__all__ = [
    'card_data_router',
    'article_router',
    'price_discount_router',
    'orders_revenues_router',
    'unit_economics_router',
    'net_profit_router',
    'percent_by_tax_router',
    'stocks_quantity_router',
    'favicon_router'
]
