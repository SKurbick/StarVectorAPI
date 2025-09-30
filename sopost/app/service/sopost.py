from reposytory.sopost import SopostRepository
from domain.shemas.sopost import SubjectsResponse


class SopostService:
    def __init__(self, repository: SopostRepository):
        self.repository = repository

    async def get_sopost_items(
        self, 
        limit: int = 100, 
        offset: int = 0,
    ) -> list[SubjectsResponse]:
        return await self.repository.get_sopost_items(limit, offset)
