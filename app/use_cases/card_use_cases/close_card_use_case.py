import logging

from app.domain.models import CardUseCaseResponse
from app.domain.enums import CardStatusEnum
from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.use_cases.card_use_cases.base import BaseCardUseCase
from celery_app.tasks.reset_wb_stocks_for_closed_card import reset_wb_stocks_for_closed_card


logger = logging.getLogger(__name__)


class CloseCardUseCase(BaseCardUseCase):
    async def execute(self, **kwargs) -> CardUseCaseResponse:
        result = CardUseCaseResponse(
            operation_type="close_card",
            all_nm_ids=[],
            invalid_nm_ids=[],
            invalid_local_codes=[],
            failed_accounts=[],
        )

        valid_nm_ids, invalid_lv_codes, invalid_nm_ids = await self.get_validated_data()

        result.all_nm_ids = valid_nm_ids
        result.invalid_nm_ids = invalid_nm_ids
        result.invalid_local_codes = invalid_lv_codes

        if not valid_nm_ids:
            return result


        card_status_repo = CardStatusRepository(self.pool)

        closed_by_account = await card_status_repo.get_cards_by_status(
            nm_ids=valid_nm_ids,
            statuses=[CardStatusEnum.closed]
        )
        closed_nm_set = {nm for nms in closed_by_account.values() for nm in nms}
        cards_to_close = [nm for nm in valid_nm_ids if nm not in closed_nm_set]


        if not cards_to_close:
            logger.info("Все запрошенные карточки уже закрыты")
            return result

        article_repo = ArticleRepository(self.pool)
        accounts_with_nm = await article_repo.get_accounts_by_nm_ids(cards_to_close)

        if not accounts_with_nm:
            logger.warning(f"Не найдены аккаунты для артикулов: {cards_to_close}")
            return result

        celery_data = {}

        for account, nm_list in accounts_with_nm.items():
            if not nm_list:
                continue

            try:
                updated = await card_status_repo.update_card_status(
                    account=account,
                    nm_ids=nm_list,
                    new_status=CardStatusEnum.closing_pending
                )

                if updated:
                    celery_data[account] = updated
            except Exception as e:
                logger.exception(f"Ошибка для аккаунта {account}: {e}")
                result.failed_accounts.append({
                    "account": account,
                    "reason": "db_error",
                    "nm_ids": nm_list,
                    "error": str(e)
                })

        if celery_data:
            reset_wb_stocks_for_closed_card.delay(data=celery_data)
            logger.info(f"Задача отправлена в Celery для аккаунтов: {list(celery_data.keys())}")

        return result
