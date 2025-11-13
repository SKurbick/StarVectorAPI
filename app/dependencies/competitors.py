from fastapi import Depends
from clickhouse_connect import get_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient as AsyncClickHouseClient

from app.config.settings import settings
from app.repository.competitors import CompetitorsRepository
from app.service.competitors import CompetitorsService


async def get_clickhouse_client() -> AsyncClickHouseClient:
    client = await get_async_client(
        host=settings.CLICKHOUSE_HOST,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB,
        port=settings.CLICKHOUSE_PORT
    )
    return client

def get_competitors_repository(client: AsyncClickHouseClient = Depends(get_clickhouse_client)) -> CompetitorsRepository:
    return CompetitorsRepository(client=client)

def get_competitors_service(repository: CompetitorsRepository = Depends(get_competitors_repository)) -> CompetitorsService:
    return CompetitorsService(repository=repository)