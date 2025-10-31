import logging

from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.service.card_scenarios.base import BaseCardService
from celery_app.tasks.reset_wb_stocks_for_closed_card import reset_wb_stocks_for_closed_card


logger = logging.getLogger(__name__)


class CloseCardService(BaseCardService):
    async def execute(self) -> dict:
        result = {
            "requested_nm_ids": set(self.nm_ids or []),
            "requested_local_codes": self.local_vendor_codes or [],
            "already_closed": [],
            "successfully_closed": [],
            "failed_accounts": [],
        }


        nm_ids = set(self.nm_ids or [])

        if self.local_vendor_codes:
            article_repo = ArticleRepository(self.pool)
            nm_from_local = await article_repo.get_articles_by_local_vendor_codes(self.local_vendor_codes)
            nm_ids.update(nm_from_local)

        result["requested_nm_ids"] = list(nm_ids)

        if not nm_ids:
            return

        card_status_repo = CardStatusRepository(self.pool)
        closed_cards = await card_status_repo.get_close_cards_by_nm_ids(list(nm_ids))
        result["already_closed"] = closed_cards
        cards_to_close = nm_ids - set(closed_cards)

        if not cards_to_close:
            logger.info("Нет карточек для закрытия")
            return

        accounts_with_data = await article_repo.get_article_barcodes(list(cards_to_close))

        if not accounts_with_data:
            logger.warning(f"Не найдены данные по артикулам: {cards_to_close}")
            return

        logger.info(f"Подготовка задачи для Celery: {list(accounts_with_data.keys())}")

        finally_data: dict[str, dict] = {}

        for account, articles in accounts_with_data.items():
            nm_ids_list = [a["nm_id"] for a in articles]
            barcodes = [a["barcode"] for a in articles if a.get("barcode")]

            if not barcodes:
                logger.warning(f"Пропуск аккаунта {account}: нет баркодов")
                result["failed_accounts"].append({
                    "account": account,
                    "reason": "no_barcodes",
                    "nm_ids": nm_ids_list
                })
                continue

            try:
                await card_status_repo.close_cards_in_account(account, nm_ids_list)
                finally_data[account] = {
                    "stocks": [{"sku": bc, "amount": 0} for bc in barcodes]
                }
                result["successfully_closed"].extend(nm_ids_list)
            except Exception as e:
                logger.exception(
                    f"Ошибка закрытия карточек для аккаунта {account}, nm_ids={nm_ids_list}: {e}"
                )
                result["failed_accounts"].append({
                    "account": account,
                    "reason": "db_error",
                    "nm_ids": nm_ids_list,
                    "error": str(e)
                })

        if finally_data:
            reset_wb_stocks_for_closed_card.delay(data=finally_data)
            logger.info(f"Задача отправлена в Celery для аккаунтов: {list(finally_data.keys())}")
        else:
            logger.info("Нет данных для отправки в Celery")

        return result