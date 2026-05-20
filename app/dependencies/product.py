from fastapi import Depends

from app.dependencies.repositories.products_repo import get_product_repository, ProductRepository
from app.dependencies.repositories.products_data_repo import get_products_data_repository, ProducsDataRepository
from app.dependencies.wb_specifications import get_wb_charc_service, get_wb_charc_repository
from app.dependencies.repositories.wb_media_repo import get_wb_media_repository
from app.dependencies.seller_account import get_seller_account_repository
from app.dependencies.product_cards import get_wb_cards_service
from app.dependencies.article import get_article_repository
from app.dependencies.card_data import get_card_data_repository
from app.dependencies.http_session import get_wb_http_session
from app.dependencies.article import get_article_repository
from app.dependencies.card_status import get_card_status_service
from app.dependencies.wb_specifications import get_wb_subject_repository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_media import WBMediaRepository
from app.repository.article import ArticleRepository
from app.repository.wb_subjects import WBSubjectRepository
from app.service.product import ProductService
from app.service.product_specifications import ProductWBSpecificationsUpdateService
from app.service.wb_specifications import WBCharcService


def get_product_service(
    product_repo: ProductRepository = Depends(get_product_repository),
    products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
    wb_media_repo: WBMediaRepository = Depends(get_wb_media_repository),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    charc_service: WBCharcService = Depends(get_wb_charc_service),
    article_repo: ArticleRepository = Depends(get_article_repository),
    wb_subject_repo: WBSubjectRepository = Depends(get_wb_subject_repository),
) -> ProductService:
    return ProductService(
        product_repo=product_repo,
        products_data_repo=products_data_repo,
        wb_media_repo=wb_media_repo,
        seller_account_repo=seller_account_repo,
        wb_charc_service=charc_service,
        article_repo=article_repo,
        wb_subject_repo=wb_subject_repo,
    )


def get_product_specifications_update_service(
    products_repo: ProductRepository = Depends(get_product_repository),
    products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
    wb_charc_repo=Depends(get_wb_charc_repository),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    article_repo=Depends(get_article_repository),
    card_data_repo=Depends(get_card_data_repository),
    wb_charc_service: WBCharcService = Depends(get_wb_charc_service),
    wb_cards_service=Depends(get_wb_cards_service),
    wb_card_status_service=Depends(get_card_status_service),
    session=Depends(get_wb_http_session),
) -> ProductWBSpecificationsUpdateService:
    return ProductWBSpecificationsUpdateService(
        products_data_repo=products_data_repo,
        products_repo=products_repo,
        wb_charc_repo=wb_charc_repo,
        seller_account_repo=seller_account_repo,
        article_repo=article_repo,
        card_data_repo=card_data_repo,
        wb_charc_service=wb_charc_service,
        wb_cards_service=wb_cards_service,
        wb_card_status_service=wb_card_status_service,
        session=session,
    )
