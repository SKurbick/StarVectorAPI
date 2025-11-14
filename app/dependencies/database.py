from asyncpg import Pool
from clickhouse_connect.driver.asyncclient import AsyncClient
from fastapi import Request
from redis.asyncio import Redis

from app.infrastructure.redis_client import redis_client


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_clickhouse_client(request: Request) -> AsyncClient:
    """Получение Сlickhouse-клиента из состояния приложения."""
    return request.app.state.clickhouse_client


def get_redis_client() -> Redis:
    return redis_client.get_client()
