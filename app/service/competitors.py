from app.repository.competitors import CompetitorsRepository
from app.domain.models import CompetitorResponseModel


class CompetitorsService:
    def __init__(self, repository: CompetitorsRepository):
        self.repository = repository

    async def get_competitors(self) -> list[CompetitorResponseModel]:
        return await self.repository.get_competitors()