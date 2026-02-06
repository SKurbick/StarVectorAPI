from asyncpg import Pool
from fastapi import Depends

from app.dependencies.article import get_article_repository
from app.dependencies.database import get_pool
from app.dependencies.http_session import get_wb_http_session
from app.service.wb_media import WBMediaService
from app.repository.wb_media import WBMediaRepository


def get_wb_media_repository(
        pool: Pool = Depends(get_pool)
) -> WBMediaRepository:
    return WBMediaRepository(pool)


def get_wb_media_service(
    wb_media_repo=Depends(get_wb_media_repository),
    article_repo=Depends(get_article_repository),
    session=Depends(get_wb_http_session),
) -> WBMediaService:
    return WBMediaService(
        wb_media_repo=wb_media_repo,
        article_repo=article_repo,
        session=session,
    )
