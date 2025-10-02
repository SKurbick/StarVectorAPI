from app.domain.models import CreateProduct, ProductResponse, SubjectDataWithProductsResponse
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
    
    async def get_product(
        self,
        product_id: str,
        repository: ProductRepository,
    ) -> ProductResponse | None:
        pass

    async def create_product(
        self,
        repository: ProductRepository,
        data: CreateProduct
    ) -> ProductResponse:
        pass

    async def update_product(
        self,
        product_id: str,
        data: CreateProduct,
        repository: ProductRepository,
    ) -> ProductResponse:
        pass

    async def delete_product(
        self,
        product_id: str,
        repository: ProductRepository,
    ) -> None:
        pass
