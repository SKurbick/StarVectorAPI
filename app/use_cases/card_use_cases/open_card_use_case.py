import logging

from app.domain.models import UseCaseResponse
from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.use_cases.card_use_cases.base import BaseCardUseCase


logger = logging.getLogger(__name__)


class OpenCardUseCase(BaseCardUseCase):
    async def execute(self) -> UseCaseResponse:
        result = UseCaseResponse(
            operation_type="open_card",
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
        active_by_account = await card_status_repo.get_cards_by_status(
            nm_ids=valid_nm_ids,
            statuses=["active"]
        )

        active_nm_set = {nm for nms in active_by_account.values() for nm in nms}
        cards_to_open = [nm for nm in valid_nm_ids if nm not in active_nm_set]

        if not cards_to_open:
            logger.info("Все запрошенные карточки уже открыты")
            return result

        article_repo = ArticleRepository(self.pool)
        accounts_with_nm = await article_repo.get_accounts_by_nm_ids(cards_to_open)

        if not accounts_with_nm:
            logger.warning(f"Не найдены аккаунты для артикулов: {cards_to_open}")
            return result

        for account, nm_list in accounts_with_nm.items():
            if not nm_list:
                continue

            try:
                updated = await card_status_repo.update_card_status(
                    account=account,
                    nm_ids=nm_list,
                    new_status="active"
                )
                if not updated:
                    logger.debug(f"Нет карточек для открытия у аккаунта {account}")
            except Exception as e:
                logger.exception(
                    f"Ошибка открытия карточек для аккаунта {account}, nm_ids={nm_list}: {e}"
                )
                result.failed_accounts.append({
                    "account": account,
                    "reason": "db_error",
                    "nm_ids": nm_list,
                    "error": str(e)
                })

        return result
