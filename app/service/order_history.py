from fastapi import HTTPException, status

from app.domain.models import OrderHistoryResponseModel
from app.repository.order_history import OrderHistoryRepository


class OrderHistoryService:
    def __init__(self, repository: OrderHistoryRepository):
        self.repository = repository

    async def get_orders_history(
            self, 
            wild: str | None
    ) -> list[OrderHistoryResponseModel]:

        # если не указан wild в query
        if not wild:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Необходимо полностью указать wild'
            )

        return await self.repository.get_orders_history(wild)