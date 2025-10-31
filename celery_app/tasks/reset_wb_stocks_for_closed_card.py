import asyncio
import logging
from contextlib import asynccontextmanager

from app.service.stocks_quantity import StocksQuantityService, StocksQuantityRepository
from app.domain.models import UpdateStocksQuantityResponseModel
from app.infrastructure.database import init_db, close_db
from celery_app.celery import celery_app


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_pool():
    """Контекстный менеджер для работы с пулом БД."""
    pool = await init_db()

    try:
        yield pool
    finally:
        await close_db(pool)


@celery_app.task(name="reset_wb_stocks_for_closed_card", bind=True)
def reset_wb_stocks_for_closed_card(self, data: dict[str, dict]):
    """Фоновая задача: обнуление остатков для закрытых карточек на Wildberries."""
    logger.info(f"Запуск задачи обнуления остатков. Аккаунты: {list(data.keys())}", )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_execute_task(data))
    except Exception as e:
        logger.exception(f"Ошибка в задаче обнуления остатков: {e}")
        raise self.retry(exc=e)
    finally:
        loop.close()

    logger.info("Задача обнуления остатков успешно завершена")


async def _execute_task(data: dict[str, dict]) -> None:
    """Асинхронная логика выполнения задачи."""
    validated_data = {
        account: UpdateStocksQuantityResponseModel(**account_data)
        for account, account_data in data.items()
    }
    logger.info(f"Данные {validated_data}")
    async with db_pool() as pool:
        repo = StocksQuantityRepository(pool=pool)
        service = StocksQuantityService(stocks_quantity_repository=repo)

        await service.edit_stocks_quantity(edit_data=validated_data)
