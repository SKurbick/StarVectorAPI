from asyncpg import Pool
from clickhouse_connect.driver.asyncclient import AsyncClient
from fastapi import Request


def get_pool(request: Request) -> Pool:
    """Получение пула соединений из состояния приложения."""
    return request.app.state.pool


def get_clickhouse_client(request: Request) -> AsyncClient:
    """Получение Сlickhouse-клиента из состояния приложения."""
    return request.app.state.clickhouse_client
