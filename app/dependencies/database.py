from asyncpg import Pool
from fastapi import Request
from redis.asyncio import Redis

from app.infrastructure.redis_client import redis_client


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_redis_client() -> Redis:
    return redis_client.get_client()
