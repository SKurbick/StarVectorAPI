import asyncio
import logging

import asyncpg

from app.celery_app import celery_app
from app.config.settings import settings


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def get_db_connection():
    """Создаёт и возвращает новое соединение с БД."""
    return await asyncpg.connect(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
    )


@celery_app.task(bind=True, max_retries=3)
def reset_wb_stocks_for_closed_card(self, nm_ids: list[int], account_name: str):
    task_id = self.request.id

    async def _run_task():
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE stock_clearance_task
                SET status = $1, updated_at = NOW(), error_message = NULL
                WHERE task_id = $2
                """,
                "started", task_id
            )
            logger.info(f"Задача {task_id} начата для {account_name}, nm_ids={nm_ids}")

            await asyncio.sleep(3)

            await conn.execute(
                """
                UPDATE stock_clearance_task
                SET status = $1, updated_at = NOW()
                WHERE task_id = $2
                """,
                "success", task_id
            )
            logger.info(f"Задача {task_id} успешно завершена - {account_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка в задаче {task_id}: {error_msg}")
            await conn.execute(
                """
                UPDATE stock_clearance_task
                SET status = $1, updated_at = NOW(), error_message = $2
                WHERE task_id = $3
                """,
                "failed", error_msg, task_id
            )
            raise
        finally:
            await conn.close()

    try:
        asyncio.run(_run_task())
    except Exception as e:
        raise self.retry(exc=e, countdown=60, max_retries=3)
