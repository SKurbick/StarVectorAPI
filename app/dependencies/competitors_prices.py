from fastapi import Depends
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.dependencies import get_clickhouse_client
from app.repository.competitors_prices import CompetitorsPricesRepository
from app.service.competitors_prices import CompetitorsPricesService


def get_competitors_prices_repository(
    client: AsyncClient = Depends(get_clickhouse_client)
) -> CompetitorsPricesRepository:
    return CompetitorsPricesRepository(client)


def get_competitors_prices_service(
    repository: CompetitorsPricesRepository = Depends(get_competitors_prices_repository)
) -> CompetitorsPricesService:
    return CompetitorsPricesService(repository)
