from typing import List
import uuid
import logging

from app.repository.article import ArticleRepository
from app.domain.models import ArticleDetails, ArticleCloseRequest
from app.tasks.wb_tasks import reset_wb_stocks_for_closed_card


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ArticleService:
    def __init__(self, article_repository: ArticleRepository):
        self.article_repository = article_repository

    # async def get_user_details(self, user_id: int) -> ArticleDetails:
    #     return await self.user_repository.get_user_details(user_id)
    async def get_article_details(self) -> List[ArticleDetails]:
        return await self.article_repository.get_article_details()

    async def close_articles(self, data: ArticleCloseRequest):
        nm_ids = set(data.nm_ids or [])

        if data.local_vendor_codes:
            nm_ids_by_local_vendor_codes = await self.article_repository.get_articles_by_local_vendor_codes(
                data.local_vendor_codes
            )
            nm_ids.update(nm_ids_by_local_vendor_codes)

        if not nm_ids:
            return

        accounts_with_nm_ids = await self.article_repository.get_accounts_by_articles(nm_ids)
        logger.info(f"{accounts_with_nm_ids}")
        logger.info(f"Начинаем передавать задачи в celery")

        for account, nm_list in accounts_with_nm_ids.items():
            await self.article_repository.close_articles_in_account(account, nm_list)

            task_id = str(uuid.uuid4())
            logger.info(f"Cоздаем задачу в БД: task_id={task_id}, acc={account}")
            await self.article_repository.create_reset_virtual_balances_task(
                task_id=task_id,
                account=account,
                nm_ids=nm_list
            )
            logger.info(f"Задача создана: task_id={task_id}, acc={account}")

            reset_wb_stocks_for_closed_card.apply_async(
                kwargs={
                    "nm_ids": nm_list,
                    "account_name": account,
                },
                task_id=task_id
            )
