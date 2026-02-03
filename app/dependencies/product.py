from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.dependencies.products_data import get_products_data_repository
from app.dependencies.wb_specifications import get_wb_charc_service
from app.dependencies.wb_media import get_wb_media_repository
from app.dependencies.seller_account import get_seller_account_repository
from app.repository.product import ProductRepository
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_media import WBMediaRepository
from app.service.product import ProductService
from app.service.wb_specifications import WBCharcService


def get_product_repository(
    pool: Pool = Depends(get_pool),
) -> ProductRepository:
    return ProductRepository(pool)


def get_product_service(
    product_repo: ProductRepository = Depends(get_product_repository),
    products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
    wb_media_repo: WBMediaRepository = Depends(get_wb_media_repository),
    seller_account_repo: SellerAccountRepository = Depends(get_seller_account_repository),
    charc_service: WBCharcService = Depends(get_wb_charc_service),
) -> ProductService:
    return ProductService(
        product_repo=product_repo,
        products_data_repo=products_data_repo,
        wb_media_repo=wb_media_repo,
        seller_account_repo=seller_account_repo,
        wb_charc_service=charc_service,
    )
