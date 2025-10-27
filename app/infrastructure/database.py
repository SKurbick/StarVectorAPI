from asyncpg import create_pool, Pool
from app.config.settings import settings


_pool: Pool | None = None


async def init_db() -> Pool:
    """Инициализация пула соединений с базой данных."""
    global _pool

    if _pool is None:
        _pool = await create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT
        )

    return _pool


async def close_db(pool: Pool) -> None:
    """Закрытие пула соединений."""
    global _pool

    p = pool or _pool

    if p is not None:
        await p.close()
        _pool = None

def get_pool() -> Pool:
    """Получить глобальный пул (для Celery и других мест вне FastAPI)."""
    if _pool is None:
        raise RuntimeError("Пул соединений не инициализирован. Вызовите init_db().")

    return _pool