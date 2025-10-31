import asyncio
import logging

import asyncpg

from app.config.settings import settings
from celery_app.celery import celery_app


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@celery_app.task(name="reset_wb_stocks_for_closed_card")
def reset_wb_stocks_for_closed_card(barcodes: list[str], account_name: str):
    logger.info(f"Запуск задачи по обнулению остатков для закрытых карточек")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(reset_wb_stocks_for_closed_card_async(
            barcodes=barcodes,
            account_name=account_name
        ))
    except Exception as e:
        logger.error(f"[Error] account: {account_name}, barcodes: {barcodes}. Error: {e}")
    
    logger.info(f"Задача по обнулению остатков для закрытых карточек завершена")
        

async def reset_wb_stocks_for_closed_card_async(barcodes: list[str], account_name: str):
    logger.info(f"Запрос на обнуление виртуальных остатков {account_name}, barcodes={barcodes}...")
    await asyncio.sleep(4)
    logger.info(f"Обнуление остатков завершено - {account_name}, barcodes={barcodes}")
