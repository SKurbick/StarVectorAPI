from app.service.stock_movement import StockMovementService


async def get_stock_movement_service() -> StockMovementService:
    return StockMovementService()
