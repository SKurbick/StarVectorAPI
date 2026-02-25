from aiohttp import ClientSession
from asyncpg import Pool
from fastapi import Depends

from app.dependencies.http_session import get_wb_http_session
from app.dependencies.database import get_pool
from app.dependencies.products_data import get_products_data_repository
from app.dependencies.marketplace_cards import get_marketplace_cards_service
from app.service.wb_specifications import WBCharcService, WBParentCategoryService, WBSubjectService
from app.repository.wb_parent_categories import WBParentCategoryRepository
from app.repository.wb_subjects import WBSubjectRepository
from app.repository.wb_charcs import WBCharcRepository
from app.repository.products_data import ProducsDataRepository
from app.service.marketplace_cards import MarketplaceCardsService


def get_wb_parent_category_repository(
        pool: Pool = Depends(get_pool)
) -> WBParentCategoryRepository:
    return WBParentCategoryRepository(pool)


def get_wb_subject_repository(
        pool: Pool = Depends(get_pool)
) -> WBSubjectRepository:
    return WBSubjectRepository(pool)


def get_wb_charc_repository(
        pool: Pool = Depends(get_pool)
) -> WBCharcRepository:
    return WBCharcRepository(pool)


def get_wb_charc_service(
        charc_repo: WBCharcRepository = Depends(get_wb_charc_repository),
        products_data_repo: ProducsDataRepository = Depends(get_products_data_repository),
        subject_repo: WBSubjectRepository = Depends(get_wb_subject_repository),
        marketplace_cards_service: MarketplaceCardsService = Depends(get_marketplace_cards_service),
        session: ClientSession = Depends(get_wb_http_session),
) -> WBCharcService:
    return WBCharcService(
        session=session,
        subject_repo=subject_repo,
        charc_repo=charc_repo,
        products_data_repo=products_data_repo,
        marketplace_cards_service=marketplace_cards_service,
    )


def get_wb_subject_service(
        repo: WBSubjectRepository = Depends(get_wb_subject_repository),
        marketplace_cards_service: MarketplaceCardsService = Depends(get_marketplace_cards_service),
) -> WBSubjectService:
    return WBSubjectService(
        repo=repo,
        marketplace_cards_service=marketplace_cards_service
    )


def get_wb_parent_category_service(
        repo: WBParentCategoryRepository = Depends(get_wb_parent_category_repository),
        marketplace_cards_service: MarketplaceCardsService = Depends(get_marketplace_cards_service),
) -> WBParentCategoryService:
    return WBParentCategoryService(
        repo=repo,
        marketplace_cards_service=marketplace_cards_service
    )
