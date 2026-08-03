from asyncpg import Pool
from fastapi import Depends
from redis.asyncio import Redis


# from app.dependencies.stock_movement import get_stock_movement_service
# from app.dependencies.database import get_pool, get_redis_client
# from app.service.stock_movement import StockMovementService
# from app.service.close_card import CloseCardService


# def get_close_card_service(
#     pool: Pool = Depends(get_pool),
#     stock_movement_service: StockMovementService = Depends(get_stock_movement_service),
#     cache_client: Redis = Depends(get_redis_client)
# ) -> CloseCardService:
#     return CloseCardService(
#         pool=pool,
#         stock_movement_service=stock_movement_service,
#         redis_client=cache_client
#     )
