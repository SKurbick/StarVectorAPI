from app.repository.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository