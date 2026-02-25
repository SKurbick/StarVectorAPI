from typing import Optional

from app.domain.models import (
    SubjectDataWithProductsResponse, 
    ProductWBCards,
)
from app.repository.product import ProductRepository
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_media import WBMediaRepository
from app.repository.article import ArticleRepository
from app.repository.wb_subjects import WBSubjectRepository
from app.service.wb_specifications import WBCharcService
from app.service.marketplace_cards import MarketplaceCardsService

class ProductService:
    """Сервисный слой для работы с товарами."""

    def __init__(
            self,
            product_repo: ProductRepository,
            products_data_repo: ProducsDataRepository,
            wb_media_repo: WBMediaRepository,
            seller_account_repo: SellerAccountRepository,
            wb_charc_service: WBCharcService,
            wb_subject_repo: WBSubjectRepository,
            article_repo: ArticleRepository,
            marketplace_cards_service: MarketplaceCardsService,
    ):
        self._product_repo = product_repo
        self._wb_charc_service = wb_charc_service
        self._wb_media_repo = wb_media_repo
        self._products_data_repo = products_data_repo
        self._seller_account_repo = seller_account_repo
        self._article_repo = article_repo
        self._wb_subject_repo = wb_subject_repo
        self._marketplace_cards_service = marketplace_cards_service

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить товары, сгруппированные по предметам."""
        return await self._product_repo.get_products_grouped_by_subjects(limit, offset)

    async def get_product_cards(self, product_id: str) -> ProductWBCards:
        """Получить карточки товара."""
        return await self._marketplace_cards_service.get_product_cards(product_id)

    async def get_product_wb_specifications(self, product_id: str):
        """Получить WB спецификации для товара."""
        return await self._marketplace_cards_service.get_product_wb_specifications(product_id)

    async def set_subject_id(self, product_id: str, subject_id: int, user_id: Optional[int] = None):
        """Присвоить предмет WB для товара."""
        product_is_exists = await self._product_repo.check_product_exists(product_id)

        if not product_is_exists:
            raise ValueError(f"Товар с id={product_id} не найден.")

        articles, _, _ = await self._article_repo.get_articles_by_criteria(local_vendor_codes=[product_id])

        if articles:
            raise RuntimeError(f"У товара id={product_id} есть созданные карточки. Предмет изменить нельзя.")

        subject_is_exists = await self._wb_subject_repo.get(subject_id)

        if not subject_is_exists:
            raise ValueError(f"Предмет с id={subject_id} не найден.")

        product_data = await self._products_data_repo.get(product_id)

        if not product_data:
            await self._products_data_repo.create(product_id, user_id)

        await self._products_data_repo.update_wb_specifications(product_id, subject_id=subject_id, user_id=user_id)
