import logging

from asyncpg import create_pool, Pool
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.config.settings import settings


logger = logging.getLogger(__name__)


async def init_postgres_db() -> Pool:
    """Инициализация пула соединений с базой данных."""
    try:
        logger.info(f"Установка соединения с базой данных PostgreSQL...")
        pool = await create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT
        )
        logger.info(f"Соединение с базой данных PostgreSQL установлено.")
        return pool
    except Exception as e:
        logger.exception(f"Ошибка при подключении к PostgreSQL: {e}")
        return None


async def close_postgres_db(pool: Pool) -> None:
    """Закрытие пула соединений."""
    if not pool:
        return

    await pool.close()
    logger.info(f"Пул соединений с PostgreSQL закрыт.")


async def init_clickhouse_client() -> AsyncClient:
    """Инициализация клиента для соединения с базой данных."""
    try:
        logger.info(f"Установка соединения с базой данных Clickhouse...")
        client = await get_async_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB,
        )
        logger.info(f"Соединение с базой данных Clickhouse установлено.")
        return client
    except Exception as e:
        logger.exception(f"Ошибка при подключении к Clickhouse: {e}")
        return None


async def close_clickhouse_client(client: AsyncClient):
    """Закрытие соединения."""
    if not client:
        return

    await client.close()
    logger.info("Соединение с Clickhouse закрыто.")
