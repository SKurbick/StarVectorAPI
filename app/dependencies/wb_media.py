from aiohttp import ClientSession
from asyncpg import Pool
from fastapi import Depends

from app.dependencies.article import get_article_repository, ArticleRepository
from app.dependencies.database import get_pool
from app.dependencies.http_session import get_wb_http_session
from app.dependencies.card_data import get_card_data_repository, CardDataRepository
from app.service.wb_media import WBMediaService
from app.repository.wb_media import WBMediaRepository


def get_wb_media_repository(
        pool: Pool = Depends(get_pool)
) -> WBMediaRepository:
    return WBMediaRepository(pool)


def get_wb_media_service(
    wb_media_repo: WBMediaRepository = Depends(get_wb_media_repository),
    article_repo: ArticleRepository = Depends(get_article_repository),
    card_data_repo: CardDataRepository = Depends(get_card_data_repository),
    session: ClientSession = Depends(get_wb_http_session),
) -> WBMediaService:
    return WBMediaService(
        wb_media_repo=wb_media_repo,
        article_repo=article_repo,
        card_data_repo=card_data_repo,
        session=session,
    )
