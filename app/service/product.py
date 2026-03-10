from typing import Optional

from app.domain.models import (
    SubjectDataWithProductsResponse, 
    ProductWBDimensionsResponse,
    ProductWBCardInfo,
    ProductWBCards,
    ProductWBSpecificationResponse,
    WBMedia,
    WBPhoto,
)
from app.repository.product import ProductRepository
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_media import WBMediaRepository
from app.repository.article import ArticleRepository
from app.repository.wb_subjects import WBSubjectRepository
from app.service.wb_specifications import WBCharcService


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
    ):
        self._product_repo = product_repo
        self._wb_charc_service = wb_charc_service
        self._wb_media_repo = wb_media_repo
        self._products_data_repo = products_data_repo
        self._seller_account_repo = seller_account_repo
        self._article_repo = article_repo
        self._wb_subject_repo = wb_subject_repo

    async def get_products_grouped_by_subjects(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SubjectDataWithProductsResponse]:
        """Получить товары, сгруппированные по предметам."""
        return await self._product_repo.get_products_grouped_by_subjects(limit, offset)

    async def get_poduct_cards(self, product_id: str) -> ProductWBCards:
        """Получить карточки товара."""
        product_wb_cards = await self._product_repo.get_product_wb_cards(product_id)
        seller_accounts = await self._seller_account_repo.get_list()
        account_vat_map = {acc.account_name.capitalize(): acc.vat_rate for acc in seller_accounts}
        wb_cards: list[ProductWBCardInfo] = []
        for item in product_wb_cards:
            video = await self._wb_media_repo.get_video_url_of_card(item.nm_id)
            cover = await self._wb_media_repo.get_cover_url_of_card(item.nm_id)
            media = WBMedia(video=video, photos=([WBPhoto(url=cover, display_order=1)] if cover else []))
            vat = account_vat_map.get(item.account.capitalize())
            card = ProductWBCardInfo(
                nm_id=item.nm_id,
                account=item.account.capitalize(),
                vendor_code=item.vendor_code,
                local_vendor_code=item.local_vendor_code,
                name=item.name,
                description=item.description,
                barcode=item.barcode,
                small_photo_link=item.small_photo_link,
                status=item.status,
                rating=item.rating,
                media=media,
                price=item.price,
                discount=item.discount,
                fbs_stock_quantity=item.fbs_stock_quantity,
                vat=f"{vat}%" if isinstance(vat, int) else "Без НДС",
                average_sales=0,
            )
            wb_cards.append(card)

        return ProductWBCards(
            id=product_id.lower(),
            wb_cards=wb_cards,
        )

    async def get_product_wb_specifications(self, product_id: str):
        """Получить WB спецификации для товара."""
        products_data = await self._products_data_repo.get(product_id)

        if not products_data:
            product_is_exists = await self._product_repo.check_product_exists(product_id)

            if not product_is_exists:
                raise ValueError(f"Товар с id={product_id} не найден.")

            await self._products_data_repo.create(product_id)
            products_data = await self._products_data_repo.get(product_id)

        subject_id = products_data.wb_subject_id
        characteristics_info = await self._wb_charc_service.get_product_charcs(product_id)
        name = products_data.name
        brand = products_data.wb_brand
        dimensions = ProductWBDimensionsResponse(
            width=products_data.wb_width or 0,
            height=products_data.wb_height or 0,
            length=products_data.wb_length or 0,
            weight_brutto=products_data.wb_weight_brutto or 0,
            volume=products_data.wb_volume or 0,
        )

        return ProductWBSpecificationResponse(
            id=product_id,
            name=name,
            subject_id=subject_id,
            brand=brand,
            dimensions=dimensions,
            characteristics=characteristics_info,
        )
    
    async def get_product_additionals(self, product_id: str) -> list[WBPhoto]:
        return await self._wb_media_repo.get_product_additionals(product_id)

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
