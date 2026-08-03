from datetime import datetime
import logging

# from app.domain.models import CloseOperationResponse, ClosedCardResult
# from app.domain.enums import CardStatusEnum
# from app.repository.card_status import CardStatusRepository
# from app.use_cases.card_use_cases.base import BaseCardUseCase
from app.infrastructure.celery_app import celery_client


logger = logging.getLogger(__name__)


# class CloseCardUseCase(BaseCardUseCase):
#     """
#     Закрытие карточек и обнуление виртуальных остатков.
#     """

#     async def execute(
#         self,
#         accounts_data: dict[str, list[int]],
#         preview_operation_id: str,
#     ) -> CloseOperationResponse:
#         timestamp = datetime.now()

#         if not accounts_data:
#             return CloseOperationResponse(
#                 operation_id=preview_operation_id,
#                 timestamp=timestamp,
#                 status="accepted",
#                 summary={},
#                 stats={
#                     "total_requested": 0,
#                     "successfully_queued": 0,
#                     "already_closed": 0,
#                     "failed_db": 0,
#                 },
#                 celery_task_ids=[],
#                 details={"failed_accounts": []}
#             )

#         card_status_repo = CardStatusRepository(self.pool)

#         nm_acc_pairs = [
#             (nm_id, account)
#             for account, nm_list in accounts_data.items()
#             for nm_id in nm_list
#         ]
#         current_statuses = await card_status_repo.get_status_by_nm_and_account(nm_acc_pairs)

#         summary: dict[str, list[ClosedCardResult]] = {}
#         failed_accounts = []

#         for account, nm_list in accounts_data.items():
#             summary[account] = []

#             for nm_id in nm_list:
#                 key = (nm_id, account)
#                 old_status = current_statuses.get(key, "active")

#                 new_status = old_status
#                 success = True
#                 error = None

#                 if old_status != CardStatusEnum.closed:
#                     try:
#                         updated = await card_status_repo.update_card_status(
#                             account=account,
#                             nm_ids=[nm_id],
#                             new_status=CardStatusEnum.closing_pending
#                         )

#                         if updated:
#                             new_status = CardStatusEnum.closing_pending.value
#                     except Exception as e:
#                         logger.exception(f"DB error for {nm_id}@{account}: {e}")
#                         success = False
#                         error = str(e)
#                         failed_accounts.append({
#                             "account": account,
#                             "nm_ids": [nm_id],
#                             "error": str(e)
#                         })

#                 summary[account].append(
#                     ClosedCardResult(
#                         nm_id=nm_id,
#                         account=account,
#                         old_status=old_status,
#                         new_status=new_status,
#                         success=success,
#                         error=error,
#                     )
#                 )


#         total_requested = sum(len(nms) for nms in accounts_data.values())
#         failed_db = sum(len(f["nm_ids"]) for f in failed_accounts)
#         successfully_queued = total_requested - failed_db
#         already_closed_count = sum(
#             1 for items in summary.values()
#             for item in items
#             if item.old_status == CardStatusEnum.closed
#         )

#         celery_task_ids = []

#         if accounts_data and successfully_queued > 0:
#             try:
#                 task = celery_client.send_task(
#                     "reset_wb_stocks_for_closed_card",
#                     kwargs={"data": accounts_data}
#                 )
#                 celery_task_ids.append(task.id)
#                 logger.info(f"Celery task {task.id} запущена для {len(accounts_data)} аккаунтов")
#             except Exception as e:
#                 message = f"Ошибка во время отпровления фоновой задачи задачи 'reset_wb_stocks_for_closed_card': {e}"
#                 logging.exception(message)
#                 raise Exception(message)

#         status = "accepted" if not failed_accounts else "partial"

#         return CloseOperationResponse(
#             operation_id=preview_operation_id,
#             timestamp=timestamp,
#             status=status,
#             summary=summary,
#             stats={
#                 "total_requested": total_requested,
#                 "successfully_queued": successfully_queued,
#                 "already_closed": already_closed_count,
#                 "failed_db": failed_db,
#             },
#             celery_task_ids=celery_task_ids,
#             details={"failed_accounts": failed_accounts}
#         )
