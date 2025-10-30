import logging
import uuid

from app.service.card_scenarios.base import BaseCardService
from app.tasks.wb_tasks import reset_wb_stocks_for_closed_card

from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.repository.celery_tasks import CeleryTaskRepository


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class CloseCardService(BaseCardService):
    async def execute(self) -> None:
        nm_ids = set(self.nm_ids)

        article_repo = ArticleRepository(self.pool)

        if self.local_vendore_codes:
            nm_ids_by_local_vendor_codes = await article_repo.get_articles_by_local_vendor_codes(
                self.local_vendore_codes
            )
            nm_ids.update(nm_ids_by_local_vendor_codes)

        if not nm_ids:
            return

        task_repo = CeleryTaskRepository(self.pool)
        card_status_repo = CardStatusRepository(self.pool)

        accounts_with_cd = await article_repo.get_article_barcodes(nm_ids)
        logger.info(f"{accounts_with_cd}")
        logger.info(f"Начинаем передавать задачи в celery")

        for account, data in accounts_with_cd.items():
            nm_ids_list = [a["nm_id"] for a in data]
            barcodes = [a["barcode"] for a in data]

            task_id = str(uuid.uuid4())
            await task_repo.create_task(
                task_id=task_id,
                account=account,
                operation_type="close_card",
                task_data={"barcodes": barcodes},
            )

            try:
                await card_status_repo.close_cards_in_account(account, nm_ids_list)
            except Exception as e:
                logger.error(f"Не удалось закрыть карточки для {account}, task_id={task_id}: {e}")

            # reset_wb_stocks_for_closed_card.apply_async(
            #     kwargs={"barcodes": barcodes, "account_name": account},
            #     task_id=task_id
            # )
