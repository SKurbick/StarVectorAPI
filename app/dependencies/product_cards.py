from asyncpg import Pool
from fastapi import Depends


from app.dependencies.article import ArticleRepository, get_article_repository
from app.dependencies.card_status import CardStatusRepository, get_card_status_repository
from app.dependencies.card_data import CardDataRepository, get_card_data_repository
from app.dependencies.database import get_pool
from app.dependencies.price_discount import PriceDiscountService, get_price_discount_service
from app.dependencies.stocks_quantity import StocksQuantityService, get_stocks_quantity_service

from app.service.product_cards import WildberriesCardsService

def get_wb_cards_service(
    article_repo: ArticleRepository = Depends(get_article_repository),
    card_status_repo: CardStatusRepository = Depends(get_card_status_repository),
    card_data_repo: CardDataRepository = Depends(get_card_data_repository),
    price_discount_service: PriceDiscountService = Depends(get_price_discount_service),
    stock_quantity_service: StocksQuantityService = Depends(get_stocks_quantity_service),
    pool: Pool = Depends(get_pool),
):
    """Получить сервис для работы с карточками WB."""
    return WildberriesCardsService(
        article_repo=article_repo,
        card_status_repo=card_status_repo,
        card_data_repo=card_data_repo,
        price_discount_service=price_discount_service,
        stock_quantity_service=stock_quantity_service,
        pool=pool,
    )
