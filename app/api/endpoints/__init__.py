from .card_data import router as card_data_router
from .article import router as article_router
from .price_discount import router as price_discount_router
from .orders_revenues import router as orders_revenues_router
from .unit_economics import router as unit_economics_router
from .net_profit import router as net_profit_router
from .percent_by_tax import router as percent_by_tax_router
from .stocks_quantity import router as stocks_quantity_router
from .favicon import router as favicon_router
from .turnover import router as turnover_router
from .product import router as product_router
from .fin_reports import router as fin_reports_router
from .penalties import router as penalties_router
from .sales import router as sales_router
from .competitors_prices import router as competitors_prices_router
from .close_card import router as close_card_router
from .open_card import router as open_card_router
from .order_history import router as orders_history_router
from .product_note import router as product_note_router


__all__ = [
    'card_data_router',
    'article_router',
    'price_discount_router',
    'orders_revenues_router',
    'unit_economics_router',
    'net_profit_router',
    'percent_by_tax_router',
    'stocks_quantity_router',
    'favicon_router',
    'turnover_router',
    'product_router',
    'fin_reports_router',
    'penalties_router',
    'sales_router',
    'competitors_prices_router',
    'close_card_router',
    'open_card_router',
    'orders_history_router',
    'product_note_router',
]
