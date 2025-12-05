from fastapi import HTTPException, status

from app.domain.models import ICNetProfitResponseModel
from app.repository.ic_net_profit import ICNetProfitRepository


class ICNetProfitService:
    def __init__(self, repository: ICNetProfitRepository):
        self.repository = repository

    async def get_net_profit(self) -> list[ICNetProfitResponseModel]:
        return await self.repository.get_net_profit()