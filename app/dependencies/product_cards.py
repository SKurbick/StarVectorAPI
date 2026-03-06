from aiohttp import ClientSession
from asyncpg import Pool
from fastapi import Depends


from app.dependencies.article import ArticleRepository, get_article_repository
from app.dependencies.card_status import CardStatusRepository, get_card_status_repository
from app.dependencies.card_data import CardDataRepository, get_card_data_repository
from app.dependencies.database import get_pool
from app.dependencies.http_session import get_wb_http_session
from app.dependencies.products_data import get_products_data_repository
from app.dependencies.wb_specifications import get_wb_charc_repository
from app.dependencies.seller_account import get_seller_account_repository
from app.dependencies.price_discount import PriceDiscountService, get_price_discount_service
from app.dependencies.stocks_quantity import StocksQuantityService, get_stocks_quantity_service
from app.dependencies.wb_media import get_wb_media_service, get_wb_media_repository
from app.service.product_cards import WildberriesCardsService
from app.service.wb_media import WBMediaService
from app.service.wb_card_create import WBCardCreateService
from app.service.wb_card_update import WBCardUpdateService
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_charcs import WBCharcRepository
from app.repository.products_data import ProducsDataRepository
from app.repository.wb_media import WBMediaRepository


def get_wb_cards_service(
    article_repo: ArticleRepository = Depends(get_article_repository),
    card_status_repo: CardStatusRepository = Depends(get_card_status_repository),
    card_data_repo: CardDataRepository = Depends(get_card_data_repository),
    price_discount_service: PriceDiscountService = Depends(get_price_discount_service),
    stock_quantity_service: StocksQuantityService = Depends(get_stocks_quantity_service),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    wb_media_repo: WBMediaRepository = Depends(get_wb_media_repository),
    wb_media_service: WBMediaService = Depends(get_wb_media_service),
    pool: Pool = Depends(get_pool),
) -> WildberriesCardsService:
    """Получить сервис для работы с карточками WB."""
    return WildberriesCardsService(
        article_repo=article_repo,
        card_status_repo=card_status_repo,
        card_data_repo=card_data_repo,
        price_discount_service=price_discount_service,
        stock_quantity_service=stock_quantity_service,
        seller_account_repo=seller_account_repo,
        wb_media_repo=wb_media_repo,
        wb_media_service=wb_media_service,
        pool=pool,
    )


def get_wb_card_update_service(
    products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
    wb_charc_repo: WBCharcRepository = Depends(get_wb_charc_repository),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    wb_cards_service: WildberriesCardsService = Depends(get_wb_cards_service),
    session: ClientSession = Depends(get_wb_http_session),
):
    """Сервис обновления карточки товара на WB."""
    return WBCardUpdateService(
        products_data_repo=products_data_repo,
        wb_charc_repo=wb_charc_repo,
        seller_account_repo=seller_account_repo,
        wb_cards_service=wb_cards_service,
        session=session,
    )


def get_wb_card_create_service(
    products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
    wb_charc_repo: WBCharcRepository = Depends(get_wb_charc_repository),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    wb_cards_service: WildberriesCardsService = Depends(get_wb_cards_service),
    wb_media_service: WBMediaService = Depends(get_wb_media_service),
    session: ClientSession = Depends(get_wb_http_session),
):
    """Сервис создания карточки товара на WB."""
    return WBCardCreateService(
        products_data_repo=products_data_repo,
        wb_charc_repo=wb_charc_repo,
        seller_account_repo=seller_account_repo,
        wb_cards_service=wb_cards_service,
        wb_media_service=wb_media_service,
        session=session,
    )
