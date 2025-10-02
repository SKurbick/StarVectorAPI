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
        return await repository.get_product(product_id)

    async def create_product(
        self,
        repository: ProductRepository,
        data: CreateProduct,
    ) -> ProductResponse:
        return await repository.create_product(data)

    async def update_product(
        self,
        product_id: str,
        data: CreateProduct,
        repository: ProductRepository,
    ) -> ProductResponse:
        return repository.update_product(
            product_id=product_id,
            data=data,
        )

    async def delete_product(
        self,
        product_id: str,
        repository: ProductRepository,
    ) -> None:
        repository.delete_product(product_id)
