from fastapi import Request, Depends
from asyncpg import Pool

from app.repository.article import ArticleRepository
from app.service.article import ArticleService


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_article_repository(pool: Pool = Depends(get_pool)) -> ArticleRepository:
    return ArticleRepository(pool)


def get_article_service(repository: ArticleRepository = Depends(get_article_repository)) -> ArticleService:
    return ArticleService(repository)
