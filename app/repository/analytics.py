

from asyncpg import Pool


class AnalyticsRepository:
    """Репозиторий для аналитических запросов"""

    def __init__(self, pool: Pool) -> None:
        self.pool = pool
