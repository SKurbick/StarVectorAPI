from asyncpg import Pool
from fastapi import Depends, Request

from app.domain.models import OrderHistoryResponseModel
from app.repository.order_history import OrderHistoryRepository
from app.service.order_history import OrderHistoryService


def get_pool(request: Request) -> Pool:
    return request.app.state.pool

def get_order_history_repository(pool: Pool = Depends(get_pool)) -> list[OrderHistoryResponseModel]:
    return OrderHistoryRepository(pool)

def get_order_history_service(repository: OrderHistoryRepository = Depends(get_order_history_repository)) -> list[OrderHistoryResponseModel]:
    return OrderHistoryService(repository)