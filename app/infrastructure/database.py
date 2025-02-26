from asyncpg import create_pool, Pool
from app.config.settings import settings


async def init_db() -> Pool:
    """Инициализация пула соединений с базой данных."""
    pool = await create_pool(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )
    return pool


async def close_db(pool: Pool) -> None:
    """Закрытие пула соединений."""
    await pool.close()
