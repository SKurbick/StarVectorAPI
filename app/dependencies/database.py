from asyncpg import Pool
from fastapi import Request


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool
