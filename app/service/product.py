from typing import Optional
from collections import defaultdict

# from app.domain.models import (
#     ProductWBDimensionsResponse,
#     ProductWBCardInfo,
#     ProductWBCards,
#     ProductWBSpecificationResponse,
#     WBMedia,
#     WBPhoto,
#     ProductWBHealth,
#     ProductWBHealthQueryParams,
#     ProductWBHealthResponse,
#     WBAccountStatus,
#     WBAccountMetrics,
#     ProductAccountWBHealthDTO,
#     ProductWBPriceStats,
#     ProductBase,
#     ProductBase,
# )
# from app.domain.enums import (
#     ProductAccountHealthWBStatus,
#     ProductWBIssueType,
#     AccountWBIssueType,
# )
# from app.repository.product import ProductRepository
# from app.repository.products_data import ProducsDataRepository
# from app.repository.seller_account import SellerAccountRepository
# from app.repository.wb_media import WBMediaRepository
# from app.repository.article import ArticleRepository
# from app.repository.wb_subjects import WBSubjectRepository
# from app.service.wb_specifications import WBCharcService


MAX_PRICE_DEVIATION = 0.2
MIN_VALID_RATING = 4.0

# class ProductService:
#     """Сервисный слой для работы с товарами."""

#     def __init__(
#             self,
#             product_repo: ProductRepository,
#             products_data_repo: ProducsDataRepository,
#             wb_media_repo: WBMediaRepository,
#             seller_account_repo: SellerAccountRepository,
#             wb_charc_service: WBCharcService,
#             wb_subject_repo: WBSubjectRepository,
#             article_repo: ArticleRepository,
#     ):
#         self._product_repo = product_repo
#         self._wb_charc_service = wb_charc_service
#         self._wb_media_repo = wb_media_repo
#         self._products_data_repo = products_data_repo
#         self._seller_account_repo = seller_account_repo
#         self._article_repo = article_repo
#         self._wb_subject_repo = wb_subject_repo

#     async def get_product_wb_group(self, product_id) -> list[ProductBase]:
#         """Получить группу объединенных товаров."""
#         return await self._products_data_repo.get_product_group_items(product_id)
    
#     async def join_to_wb_group(self, target: str, product_ids: list[str]):
#         """Добавить товары в группу для склейки карточек на ВБ."""
#         if not product_ids:
#             raise ValueError(f"Передан пустой список товаров.")

#         target_product_data = await self._products_data_repo.get(target)

#         if not target_product_data:
#             product_is_exists = await self._product_repo.check_product_exists(target)

#             if not product_is_exists:
#                 raise ValueError(f"Товар с id={target} не найден.")

#             raise ValueError(f"Товару {target} не присвоен предмет.")

#         if not target_product_data.wb_subject_id:
#             raise ValueError(f"Товару {target} не присвоен предмет.")

#         for p_id in product_ids:
#             product_data = await self._products_data_repo.get(p_id)

#             if not product_data:
#                 product_is_exists = await self._product_repo.check_product_exists(p_id)

#                 if not product_is_exists:
#                     raise ValueError(f"Товар с id={p_id} не найден.")

#                 raise ValueError(f"Товару {p_id} не присвоен предмет.")

#             if not product_data.wb_subject_id:
#                 raise ValueError(f"Товару {p_id} не присвоен предмет.")

#             if target_product_data.wb_subject_id != product_data.wb_subject_id:
#                 raise ValueError(f"Предмет товара с id={p_id} не соответсвует предмету группы.")

#         await self._products_data_repo.join_to_wb_group(target, product_ids)

#     async def split_from_wb_group(self, product_ids: list[str]):
#         """Отсоединить товары из группы для склейки карточек на ВБ."""
#         current_subject = None

#         for p_id in product_ids:
#             product_data = await self._products_data_repo.get(p_id)

#             if not product_data:
#                 product_is_exists = await self._product_repo.check_product_exists(p_id)

#                 if not product_is_exists:
#                     raise ValueError(f"Товар с id={p_id} не найден.")

#                 raise ValueError(f"Товару {p_id} не присвоен предмет.")

#             if not product_data.wb_subject_id:
#                 raise ValueError(f"Товару {p_id} не присвоен предмет.")
            
#             if current_subject is None:
#                 current_subject = product_data.wb_subject_id
#                 continue

#             if product_data.wb_subject_id != current_subject:
#                 raise ValueError(f"Предметы товаров отличаются для объединения в группу.")

#         await self._products_data_repo.split_from_wb_group(product_ids)

#     async def get_poduct_cards(self, product_id: str) -> ProductWBCards:
#         """Получить карточки товара."""
#         product_wb_cards = await self._product_repo.get_product_wb_cards(product_id)
#         seller_accounts = await self._seller_account_repo.get_list()
#         account_vat_map = {acc.account_name.capitalize(): acc.vat_rate for acc in seller_accounts}
#         wb_cards: list[ProductWBCardInfo] = []
#         for item in product_wb_cards:
#             video = await self._wb_media_repo.get_video_url_of_card(item.nm_id)
#             cover = await self._wb_media_repo.get_cover_url_of_card(item.nm_id)
#             media = WBMedia(video=video, photos=([WBPhoto(url=cover, display_order=1)] if cover else []))
#             vat = account_vat_map.get(item.account.capitalize())
#             card = ProductWBCardInfo(
#                 nm_id=item.nm_id,
#                 account=item.account.capitalize(),
#                 vendor_code=item.vendor_code,
#                 local_vendor_code=item.local_vendor_code,
#                 name=item.name,
#                 description=item.description,
#                 barcode=item.barcode,
#                 small_photo_link=item.small_photo_link,
#                 status=item.status,
#                 rating=item.rating,
#                 media=media,
#                 price=item.price,
#                 discount=item.discount,
#                 fbs_stock_quantity=item.fbs_stock_quantity,
#                 vat=f"{vat}%" if isinstance(vat, int) else "Без НДС",
#                 average_sales=0,
#             )
#             wb_cards.append(card)

#         return ProductWBCards(
#             id=product_id.lower(),
#             wb_cards=wb_cards,
#         )

#     async def get_product_wb_specifications(self, product_id: str):
#         """Получить WB спецификации для товара."""
#         products_data = await self._products_data_repo.get(product_id)

#         if not products_data:
#             product_is_exists = await self._product_repo.check_product_exists(product_id)

#             if not product_is_exists:
#                 raise ValueError(f"Товар с id={product_id} не найден.")

#             await self._products_data_repo.create(product_id)
#             products_data = await self._products_data_repo.get(product_id)

#         subject_id = products_data.wb_subject_id
#         characteristics_info = await self._wb_charc_service.get_product_charcs(product_id)
#         name = products_data.name
#         brand = products_data.wb_brand
#         default_cards_name = products_data.wb_default_title
#         default_cards_description = products_data.wb_default_description
#         dimensions = ProductWBDimensionsResponse(
#             width=products_data.wb_width or 0,
#             height=products_data.wb_height or 0,
#             length=products_data.wb_length or 0,
#             weight_brutto=products_data.wb_weight_brutto or 0,
#             volume=products_data.wb_volume or 0,
#         )

#         return ProductWBSpecificationResponse(
#             id=product_id,
#             name=name,
#             subject_id=subject_id,
#             brand=brand,
#             dimensions=dimensions,
#             default_cards_name=default_cards_name,
#             default_cards_description=default_cards_description,
#             characteristics=characteristics_info,
#         )
    
#     async def get_product_additionals(self, product_id: str) -> list[WBPhoto]:
#         return await self._wb_media_repo.get_product_additionals(product_id)

#     async def set_subject_id(self, product_id: str, subject_id: int, user_id: Optional[int] = None):
#         """Присвоить предмет WB для товара."""
#         product_is_exists = await self._product_repo.check_product_exists(product_id)

#         if not product_is_exists:
#             raise ValueError(f"Товар с id={product_id} не найден.")

#         articles, _, _ = await self._article_repo.get_articles_by_criteria(local_vendor_codes=[product_id])

#         if articles:
#             raise RuntimeError(f"У товара id={product_id} есть созданные карточки. Предмет изменить нельзя.")

#         subject_is_exists = await self._wb_subject_repo.get(subject_id)

#         if not subject_is_exists:
#             raise ValueError(f"Предмет с id={subject_id} не найден.")

#         product_data = await self._products_data_repo.get(product_id)

#         if not product_data:
#             await self._products_data_repo.create(product_id, user_id)

#         await self._products_data_repo.update_wb_subject(product_id, subject_id=subject_id, user_id=user_id)

#     async def get_products_wb_health_analitics(self, params: ProductWBHealthQueryParams):
#         db_result: list[ProductAccountWBHealthDTO] = await self._product_repo.get_products_wb_health_analitics(params)

#         products_map: dict[str, list] = defaultdict(list)
#         product_ids = []
#         total = 0

#         if db_result:
#             total = db_result[0].total_count

#         for row in db_result:
#             products_map[row.product_id].append(row)
#             product_ids.append(row.product_id)

#         items = []
#         for _, rows in products_map.items():
#             product_item = self._build_product_stats(rows)
#             items.append(product_item)

#         return ProductWBHealthResponse(
#             meta={
#                 "total": total,
#                 "page": params.page,
#                 "page_size": params.size
#             },
#             data=items
#         )

#     def _build_product_stats(
#         self, 
#         rows: list[ProductAccountWBHealthDTO],
#     ) -> ProductWBHealth:
#         accounts = []
#         global_issues = []

#         global_stats_source = rows[0]
#         product_id = global_stats_source.product_id
#         product_name = global_stats_source.product_name
#         product_photo_link = global_stats_source.product_photo_link
#         current_physical_quantity = global_stats_source.current_physical_quantity
#         max_price = global_stats_source.max_price
#         min_price = global_stats_source.min_price
#         is_warning_price_deviation = global_stats_source.is_warning_price_deviation
#         global_status = global_stats_source.global_status
#         deviation_percent = round((max_price - min_price) / min_price * 100, 0) if min_price else None

#         price_stats = ProductWBPriceStats(
#             max_active_price=max_price,
#             min_active_price=min_price,
#             deviation_percent=deviation_percent,
#         )

#         if is_warning_price_deviation:
#             global_issues.append(ProductWBIssueType.PRICE_DEVIATION)

#         for row in rows:
#             if not product_photo_link:
#                 product_photo_link = row.product_photo_link

#             issues = []
#             status = ProductAccountHealthWBStatus.OK

#             if row.is_warning_no_active_cards:
#                 issues.append(AccountWBIssueType.NO_ACTIVE_CARDS)
#                 status = ProductAccountHealthWBStatus.WARNING

#             if row.is_warning_no_active_cards and row.is_warning_ready_to_activate:
#                 issues.append(AccountWBIssueType.READY_TO_ACTIVATE)
#                 status = ProductAccountHealthWBStatus.WARNING

#             if (
#                 row.active_rating is not None
#                 and row.active_rating > 0 
#                 and row.active_rating < MIN_VALID_RATING
#             ):
#                 issues.append(AccountWBIssueType.LOW_RATING)
#                 status = ProductAccountHealthWBStatus.WARNING

#             if row.is_error_multiple_cards:
#                 issues.append(AccountWBIssueType.MULTIPLE_ACTIVE_CARDS)
#                 status = ProductAccountHealthWBStatus.ERROR

#             if row.is_error_vat_mismatch:
#                 issues.append(AccountWBIssueType.VAT_MISMATCH)
#                 status = ProductAccountHealthWBStatus.ERROR

#             accounts.append(WBAccountStatus(
#                 account_id=row.account_id,
#                 account_name=row.account_name,
#                 status=status,
#                 issues=issues,
#                 metrics=WBAccountMetrics(
#                     active_nm_id=row.active_nm_id,
#                     active_cards_count=row.active_cards_count,
#                     ready_to_activate_nm_id=row.ready_to_activate_nm_id,
#                     ready_to_activate_cards_count=row.ready_to_activate_cards_count,
#                     current_vat=row.active_vat,
#                     account_vat=row.account_vat,
#                     best_rating=row.active_rating,
#                     active_price=row.active_price
#                 )
#             ))

#         return ProductWBHealth(
#             product_id=product_id,
#             product_name=product_name,
#             active_photo_link=product_photo_link,
#             global_status=global_status,
#             global_issues=global_issues,
#             price_stats=price_stats,
#             current_physical_quantity=current_physical_quantity,
#             accounts=accounts
#         )

#     async def get_products_by_wb_subject(self, subject_id: int) -> list[ProductBase]:
#         """Получить товары по предмету WB."""
#         return await self._product_repo.get_products_by_wb_subject(subject_id)
