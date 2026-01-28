from asyncpg import Pool
from fastapi import Depends

from app.dependencies.database import get_pool
from app.repository import AnalyticsRepository
from app.service import AnalyticsService



def get_analytics_repository(pool: Pool = Depends(get_pool)) -> AnalyticsRepository:
    return AnalyticsRepository(pool)


def get_analytics_service(repository: AnalyticsRepository = Depends(get_analytics_repository)) -> AnalyticsService:
    return AnalyticsService(repository)
