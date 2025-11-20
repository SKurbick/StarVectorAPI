from datetime import date
from fastapi import HTTPException, status

from app.domain.models import OrderHistoryResponseModel
from app.repository.order_history import OrderHistoryRepository


class OrderHistoryService:
    def __init__(self, repository: OrderHistoryRepository):
        self.repository = repository

    async def get_orders_history(
            self, 
            product_id: str, 
            start: date,
            end: date
    ) -> list[OrderHistoryResponseModel]:

        # если не указан wild в query
        if not product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Необходимо полностью указать wild'
            )
        
        if start and start > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Начало периода не может быть больше сегодняшней даты'
            )
        
        if start and not isinstance(start, date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный тип данных. Введите дату в формате ГГГГ-ММ-ДД"
            )
        
        if end and not isinstance(end, date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный тип данных. Введите дату в формате ГГГГ-ММ-ДД"
            )

        return await self.repository.get_orders_history(product_id, start, end)