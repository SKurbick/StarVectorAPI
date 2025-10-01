from app.domain.models import SubjectDataWithProductsResponse
from app.repository.product import ProductRepository


class ProductService:
    """Сервисный слой для работы с товарами."""

    def __init__(self, repository: ProductRepository):
        self.repository = repository

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить товары, сгруппированные по предметам."""
        return await self.repository.get_products_grouped_by_subjects(limit, offset)
