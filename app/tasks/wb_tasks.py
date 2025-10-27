import asyncio

from app.infrastructure.database import get_pool
from app.repository.task_repository import TaskRepository
from app.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def clear_wb_stocks_for_closed_card(self, nm_ids: list[int], account_name: str):
    task_id = self.request.id

    def run_async():
        pool = get_pool()
        repo = TaskRepository(pool)

        async def work():
            await repo.update_task_status(task_id, "started")
            print(f"Обнуление для {account_name}, nm_ids={nm_ids}")
            await asyncio.sleep(2)  # имитация работы
            await repo.update_task_status(task_id, "success")

        asyncio.run(work())

    try:
        run_async()
    except Exception as e:
        print(f"Ошибка: {e}")
        asyncio.run(TaskRepository(get_pool()).update_task_status(task_id, "failed", str(e)))
        raise self.retry(exc=e, countdown=60, max_retries=3)
