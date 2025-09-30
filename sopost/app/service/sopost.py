from reposytory.sopost import SopostRepository
from domain.shemas.sopost import SopostItemResponse


class SopostService:
    def __init__(self, repository: SopostRepository):
        self.repository = repository

    async def get_sopost_items(
        self, 
        limit: int, 
        offset: int
    ) -> list[SopostItemResponse]:
        return await self.repository.get_sopost_items(limit, offset)
