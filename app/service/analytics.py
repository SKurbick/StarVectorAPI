from app.domain.models import AnalyticsTimeExecutingWithWBAccount
from app.repository.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    async def get_warehouse_time_execution(self):
        """
        Получить время выполнения заказа со склада для каждого аккаунта ВБ

        Считается от созданной заявки до перевода заявки на стороне ВБ в сортировку
        """
        row = await self.repository.get_warehouse_time_execution()
        return [AnalyticsTimeExecutingWithWBAccount(**r) for r in row]
