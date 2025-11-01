import logging

from app.repository.card_status import CardStatusRepository
from app.use_cases.card_use_cases.base import BaseCardUseCase
from app.domain.models import UseCaseResponse


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

        valid_data, invalid_nm_ids = await self.get_validated_data()
        nm_ids = []

        for _, nms in valid_data.items():
            nm_ids.extend([nm["nm_id"] for nm in nms])

        print(f"Данные {nm_ids}")
        result.all_nm_ids.extend(nm_ids)
        result.invalid_nm_ids.extend(invalid_nm_ids)

        if not nm_ids:
            return result

        card_status_repo = CardStatusRepository(self.pool)

        for account, articles in valid_data.items():
            nm_ids_list = [a["nm_id"] for a in articles]
            try:
                await card_status_repo.open_cards(account, nm_ids_list)
            except Exception as e:
                logger.exception(
                    f"Ошибка закрытия карточек для аккаунта {account}, nm_ids={nm_ids_list}: {e}"
                )
                result.failed_accounts.append({
                    "account": account,
                    "reason": "db_error",
                    "nm_ids": nm_ids_list,
                    "error": str(e)
                })

        return result
