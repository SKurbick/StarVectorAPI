from asyncpg import Pool
from fastapi import Depends
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.dependencies import get_clickhouse_client, get_pool
from app.repository.competitors_prices import CompetitorPriceRepository
from app.service.competitors_prices import CompetitorPriceService


def get_competitor_price_repository(
    pool: Pool = Depends(get_pool),
    client: AsyncClient = Depends(get_clickhouse_client)
) -> CompetitorPriceRepository:
    return CompetitorPriceRepository(
        client=client,
        pool=pool,
    )


def get_competitor_price_service(
    repository: CompetitorPriceRepository = Depends(get_competitor_price_repository)
) -> CompetitorPriceService:
    return CompetitorPriceService(repository)
