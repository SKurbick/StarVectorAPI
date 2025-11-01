import asyncio
import logging
from contextlib import asynccontextmanager

from app.domain.models import UpdateStocksQuantityResponseModel, SkuAmountResponseModel
from app.infrastructure.database import init_db, close_db
from app.repository.card_status import CardStatusRepository
from app.service.stocks_quantity import StocksQuantityService, StocksQuantityRepository
from celery_app.celery import celery_app


logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_pool():
    pool = await init_db()

    try:
        yield pool
    finally:
        await close_db(pool)


@celery_app.task(name="reset_wb_stocks_for_closed_card", bind=True)
def reset_wb_stocks_for_closed_card(self, data: dict[str, list[int]]):
    """Обнуление остатков для закрытых карточек."""
    logger.info(f"Запуск задачи обнуления остатков. Аккаунты: {list(data.keys())}")

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


async def _execute_task(data: dict[str, list[int]]) -> None:
    async with db_pool() as pool:
        barcodes_by_account = {}

        for account, nm_ids in data.items():
            if not nm_ids:
                continue

            query = """
                SELECT cd.barcode
                FROM card_data cd
                WHERE cd.article_id = ANY($1)
            """
            rows = await pool.fetch(query, nm_ids)
            barcodes = [row["barcode"] for row in rows if row["barcode"]]

            if barcodes:
                barcodes_by_account[account] = [
                    SkuAmountResponseModel(sku=bc, amount=0) for bc in barcodes
                ]

        if not barcodes_by_account:
            logger.warning("Не найдены баркоды для обнуления")
            return

        edit_data = {
            account: UpdateStocksQuantityResponseModel(stocks=stocks)
            for account, stocks in barcodes_by_account.items()
        }

        stocks_repo = StocksQuantityRepository(pool=pool)
        service = StocksQuantityService(stocks_quantity_repository=stocks_repo)
        await service.edit_stocks_quantity(edit_data=edit_data)

        card_status_repo = CardStatusRepository(pool=pool)

        for account, nm_ids in data.items():
            await card_status_repo.update_card_status(
                account=account,
                nm_ids=nm_ids,
                new_status="closed",
                from_status="closing_pending"
            )
