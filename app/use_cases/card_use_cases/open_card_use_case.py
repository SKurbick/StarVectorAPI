import logging

from app.infrastructure.marketplace_card_manager.schemas import OpenCardsRequest
from app.domain.enums import CardStatusEnum
from app.repository.card_status import CardStatusRepository
from app.use_cases.card_use_cases.base import BaseCardUseCase


logger = logging.getLogger(__name__)


class OpenCardUseCase(BaseCardUseCase):
    async def execute(self, data: OpenCardsRequest):
        result = dict(
            operation_type="open_card",
            all_nm_ids={},
            invalid_nm_ids=[],
            invalid_local_codes=[],
            failed_accounts=[],
        )

        valid_by_account, invalid_lvc, invalid_nm = await self.get_validated_data(data)

        result["all_nm_ids"] = valid_by_account
        result["invalid_local_codes"] = invalid_lvc
        result["invalid_nm_ids"] = invalid_nm

        if not valid_by_account:
            return result

        card_status_repo = CardStatusRepository(self.pool)

        for account, nm_ids in valid_by_account.items():
            if not nm_ids:
                continue

            try:
                updated = await card_status_repo.update_card_status(
                    account=account,
                    nm_ids=nm_ids,
                    new_status=CardStatusEnum.active,
                )
                if updated:
                    logger.info(f"Аккаунт {account}: открыто {len(updated)} карточек: {updated}")
                else:
                    logger.debug(f"Аккаунт {account}: все карточки уже открыты")
            except Exception as e:
                logger.exception(f"Ошибка открытия карточек для аккаунта {account}: {e}")
                result["failed_accounts"].append({
                    "account": account,
                    "nm_ids": nm_ids,
                    "error": str(e),
                })

        return result
