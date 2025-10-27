from typing import List

from app.repository.article import ArticleRepository
from app.domain.models import ArticleDetails, ArticleCloseRequest


class ArticleService:
    def __init__(self, article_repository: ArticleRepository):
        self.article_repository = article_repository

    # async def get_user_details(self, user_id: int) -> ArticleDetails:
    #     return await self.user_repository.get_user_details(user_id)
    async def get_article_details(self) -> List[ArticleDetails]:
        return await self.article_repository.get_article_details()

    async def close_articles(self, data: ArticleCloseRequest):
        # nm_ids = set(data.nm_ids or [])

    #     if data.local_vendor_codes:
    #         nm_ids_by_local_vendor_codes = await self.article_repository.get_articles_by_local_vendor_codes(
    #             data.local_vendor_codes
    #         )
    #         nm_ids.update(nm_ids_by_local_vendor_codes)

    #     if not nm_ids:
    #         return

    # accounts_with_nm_ids = await self.article_repository.get_accounts_by_articles(nm_ids)
        accounts_with_nm_ids = {
            "ВЕКТОР": [574356730, 560723071],
            "ВЕКТОР2": [560703153, 574385815],
            "ОГАНЕСЯН": [560720080, 574371016],
            "ПИЛОСЯН": [560712615, 574381131],
            "СТАРТ": [560714678, 574375967],
            "СТАРТ2": [574385514, 560710142],
            "ТОНОЯН": [560721345, 574365632],
            "ХАЧАТРЯН": [574372563, 560717249],
        }


        for account, nm_list in accounts_with_nm_ids.items():
            await self.article_repository.close_articles_in_account(account, nm_list)
