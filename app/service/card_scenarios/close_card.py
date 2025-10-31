import logging

from app.service.card_scenarios.base import BaseCardService
from celery_app.tasks.reset_wb_stocks_for_closed_card import reset_wb_stocks_for_closed_card

from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository


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
        article_repo = ArticleRepository(self.pool)
        card_status_repo = CardStatusRepository(self.pool)

        nm_ids = self.nm_ids

        if self.local_vendore_codes:
            nm_ids_by_local_vendor_codes = await article_repo.get_articles_by_local_vendor_codes(
                self.local_vendore_codes
            )
            nm_ids.extend([nm_id for nm_id in nm_ids_by_local_vendor_codes if nm_id not in nm_ids])
        
        closed_cards = await card_status_repo.get_close_cards_by_nm_ids(nm_ids)
        finally_cards_to_close = [nm_id for nm_id in nm_ids if nm_id not in closed_cards]

        if not finally_cards_to_close:
            return

        accounts_with_cd = await article_repo.get_article_barcodes(finally_cards_to_close)
        logger.info(f"{accounts_with_cd}")
        logger.info(f"Начинаем передавать задачи в celery")

        finally_data = {}

        for account, data in accounts_with_cd.items():
            nm_ids_list = [a["nm_id"] for a in data]
            barcodes = [a["barcode"] for a in data]

            try:
                await card_status_repo.close_cards_in_account(account, nm_ids_list)
            except Exception as e:
                logger.error(f"Не удалось закрыть карточки для {account}, nm_ids_list={nm_ids_list}: {e}")
            
            if barcodes:
                if account not in finally_data:
                    finally_data[account] = {
                        "stocks" :[{
                            "sku": barcode,
                            "amount": 0
                        } for barcode in barcodes]
                    }

        reset_wb_stocks_for_closed_card.delay(data=finally_data)
