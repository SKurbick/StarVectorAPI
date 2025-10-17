from asyncpg import create_pool, Pool
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.config.settings import settings


async def init_postgres_db() -> Pool:
    """Инициализация пула соединений с базой данных."""
    pool = await create_pool(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )
    return pool


async def close_postgres_db(pool: Pool) -> None:
    """Закрытие пула соединений."""
    await pool.close()


async def init_clickhouse_client() -> AsyncClient:
    """Инициализация клиента для соединения с базой данных."""
    client = await get_async_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB,
    )

    return client


async def close_clickhouse_client(client: AsyncClient):
    """Закрытие соединения."""
    await client.close()
