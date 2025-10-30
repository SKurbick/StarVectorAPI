from typing import List

from app.repository.article import ArticleRepository
from app.domain.models import ArticleDetails


class ArticleService:
    def __init__(self, article_repository: ArticleRepository):
        self.article_repository = article_repository

    # async def get_user_details(self, user_id: int) -> ArticleDetails:
    #     return await self.user_repository.get_user_details(user_id)
    async def get_article_details(self) -> List[ArticleDetails]:
        return await self.article_repository.get_article_details()
