from datetime import date
from fastapi import HTTPException, status

from app.domain.models import OrderHistoryResponseModel
from app.repository.order_history import OrderHistoryRepository


class OrderHistoryService:
    def __init__(self, repository: OrderHistoryRepository):
        self.repository = repository

    async def get_orders_history(
            self, 
            start_day: date | None, 
            end_day: date | None
    ) -> list[OrderHistoryResponseModel]:

        # обработка ошибки: если указаны start_day и end_day и start_day > end_day
        if start_day and end_day and start_day > end_day:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start_day cannot be greater than end_day"
            )
            
        # если start_day = будущей дате
        if start_day and start_day > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Start_day is in the future'
        )

        return await self.repository.get_orders_history(start_day=start_day, end_day=end_day)