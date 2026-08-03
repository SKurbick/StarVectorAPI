import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiohttp import ClientSession

# from app.domain.enums import PredefinedWBCharcEnum, CertificationCharсEnum, CardStatusEnum
# from app.domain.models import (
#     ProductWBSpecificationUpdate,
#     CardCharcsUpdate,
#     WBCardUpdate,
#     DimensionsUpdate,
#     SizeUpdate,
#     WBCharc,
# )
# from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI, Card
# from app.repository.article import ArticleRepository
# from app.repository.card_data import CardDataRepository
# from app.repository.products_data import ProducsDataRepository
# from app.repository.seller_account import SellerAccountRepository
# from app.repository.product import ProductRepository
# from app.repository.wb_charcs import WBCharcRepository
# from app.service.product_cards import WildberriesCardsService
# from app.service.wb_specifications import WBCharcService
# from app.service.card_status import CardStatusService


# logger = logging.getLogger(__name__)


# class ProductWBSpecificationsUpdateService:
#     """Сервис обновления WB-спецификаций товара."""

#     def __init__(
#         self,
#         products_repo: ProductRepository,
#         products_data_repo: ProducsDataRepository,
#         wb_charc_repo: WBCharcRepository,
#         seller_account_repo: SellerAccountRepository,
#         article_repo: ArticleRepository,
#         card_data_repo: CardDataRepository,
#         wb_charc_service: WBCharcService,
#         wb_cards_service: WildberriesCardsService,
#         wb_card_status_service: CardStatusService,
#         session: ClientSession,
#     ):
#         self._products_data_repo = products_data_repo
#         self._wb_charc_repo = wb_charc_repo
#         self._seller_account_repo = seller_account_repo
#         self._article_repo = article_repo
#         self._card_data_repo = card_data_repo
#         self._wb_charc_service = wb_charc_service
#         self._wb_cards_service = wb_cards_service
#         self._wb_card_status_service = wb_card_status_service
#         self._products_repo = products_repo
#         self._session = session

#     async def update_product_specifications(self, data: ProductWBSpecificationUpdate, user_id: Optional[int] = None) -> tuple[list[dict], list[str]]:
#         """
#         Обновить спецификации товара и все его карточки на WB.
#         Возвращает список nm_id обновлённых карточек.
#         """
#         product_data = await self._products_data_repo.get(data.id)

#         if not product_data:
#             product_is_exists = await self._products_repo.check_product_exists(data.id)

#             if not product_is_exists:
#                 raise ValueError(f"Товар с id={data.id} не найден.")

#             await self._products_data_repo.create(data.id)
#             product_data = await self._products_data_repo.get(data.id)

#         subject_with_actual_charcs = await self._wb_charc_service.get_charcs_by_subject_id(product_data.wb_subject_id)
#         actual_chars = subject_with_actual_charcs.charcs
#         final_charcs = self._build_final_charcs(actual_chars, data.characteristics)

#         await self._products_data_repo.update_wb_specifications(
#             product_id=data.id,
#             width=data.dimensions.width,
#             height=data.dimensions.height,
#             length=data.dimensions.length,
#             weight_brutto=data.dimensions.weight_brutto,
#             brand=data.brand or None,
#             default_title=data.default_values.values.card_title or None,
#             default_description=data.default_values.values.card_description or None,
#             user_id=user_id,
#         )

#         await self._wb_charc_repo.replace_product_charcs(
#             product_id=data.id,
#             charcs=final_charcs,
#             user_id=user_id,
#         )

#         articles, _, _ = await self._article_repo.get_articles_by_criteria(
#             local_vendor_codes=[data.id]
#         )

#         if not articles:
#             return [], []

#         cards_by_account: dict[str, list[int]] = {}

#         for item in articles:
#             cards_by_account.setdefault(item["account"], []).append(item["nm_id"])

#         updated_cards: list[dict] = []
#         errors: list[str] = []

#         update_tasks = []
#         for account, nm_ids in cards_by_account.items():
#             update_tasks.append(asyncio.create_task(self._update_cards_on_account(
#                 account=account,
#                 nm_ids=nm_ids,
#                 data=data,
#                 common_charcs=final_charcs,
#                 user_id=user_id,
#             )))

#         results = await asyncio.gather(*update_tasks)

#         for (res_updated, res_errors) in results:
#             updated_cards.extend(res_updated)
#             errors.extend(res_errors)

#         return updated_cards, errors

#     async def _update_cards_on_account(
#         self, 
#         account: str,
#         nm_ids: list[int],
#         data: ProductWBSpecificationUpdate,
#         common_charcs: list[CardCharcsUpdate],
#         user_id: Optional[int] = None,
#     ):
#         errors: list[str] = []
#         updated_cards: list[dict] = []

#         wb_client = CardsWBAPI(account_name=account, session=self._session)
#         vat_charc = await self._get_vat_charc(account)
#         update_cards: list[WBCardUpdate] = []

#         force_update_uniq_attrs = data.default_values.force_update
#         default_values_for_uniq_attrs = data.default_values.values

#         exists_cards_for_update = await self._try_get_exists_cards(
#             nm_ids=nm_ids,
#             wb_client=wb_client
#         )


#         for card in exists_cards_for_update:
#             certificate_charcs = self._get_certificate_chars(card.characteristics)
#             sizes = [
#                 SizeUpdate(
#                     chrt_id=size.chrt_id,
#                     tech_size=size.tech_size,
#                     wb_size=size.wb_size,
#                     price=size.price,
#                     skus=size.skus,
#                 )
#                 for size in card.sizes
#             ]

#             title = card.title or ""
#             description = card.description or ""

#             normilize_title = title.strip()
#             normilize_description = description.strip()

#             if not normilize_title or (normilize_title and force_update_uniq_attrs):
#                 normilize_title = default_values_for_uniq_attrs.card_title
            
#             if not normilize_description or (normilize_description and force_update_uniq_attrs):
#                 normilize_description = default_values_for_uniq_attrs.card_description

#             update_cards.append(
#                 WBCardUpdate(
#                     nm_id=card.nm_id,
#                     vendor_code=card.vendor_code,
#                     brand=data.brand or "",
#                     title=normilize_title or "",
#                     description=normilize_description or "",
#                     dimensions=DimensionsUpdate(
#                         width=data.dimensions.width,
#                         height=data.dimensions.height,
#                         length=data.dimensions.length,
#                         weight_brutto=data.dimensions.weight_brutto,
#                     ),
#                     characteristics=[
#                         *common_charcs,
#                         *certificate_charcs,
#                         vat_charc,
#                     ],
#                     sizes=sizes,
#                 )
#             )

#         if update_cards:
#             result = await self._wb_cards_service.update_cards_from_request(
#                 wb_client=wb_client,
#                 update_cards=update_cards,
#                 user_id=user_id,
#             )
#             updated_cards.extend(
#                 [{"account": account, "nm_id": nm_id} for nm_id in result.updated]
#             )
#             errors.extend(result.errors)

#         await self._update_card_data_dimensions(
#             [item["nm_id"] for item in updated_cards],
#             data,
#             user_id,
#         )

#         return updated_cards, errors

#     async def _try_get_exists_cards(
#         self,
#         nm_ids: list[int],
#         wb_client: CardsWBAPI,
#     ) -> list[Card]:
#         """
#         Получить существующие карточки товара с маркетплейса.
#         """
#         statuses_of_cards = await self._wb_card_status_service.get_status_by_nm_ids(nm_ids=nm_ids)
#         tasks = []
        
#         for nm_id in nm_ids:
#             card_status = statuses_of_cards.get(nm_id)
#             if card_status in {CardStatusEnum.deleted, CardStatusEnum.trashed}:
#                 logger.debug(f"Статус карточки [{nm_id=}|{card_status=}]. Пропускаем.")
#                 continue

#             tasks.append(asyncio.create_task(self._try_get_card_fron_wb(
#                 nm_id=nm_id,
#                 wb_client=wb_client,
#             )))
        
#         results = await asyncio.gather(*tasks, return_exceptions=True)

#         valid_cards = []

#         for res in results:
#             if isinstance(res, Exception):
#                 logger.exception(f"Ошибка во время попытки получить карточку с ВБ: {res}")
#                 continue

#             if res is not None:
#                 valid_cards.append(res)

#         logger.debug(f"Найдено карточек: [{wb_client.account_name}|{len(valid_cards)}/{len(tasks)}]")
#         return valid_cards

#     @staticmethod
#     async def _try_get_card_fron_wb(
#         nm_id: int,
#         wb_client: CardsWBAPI
#     ) -> Card | None:
#         """
#         Получить карточку с маркетплейса с несколькими попытками.
#         """
#         wb_card = None
#         attemp_count = 3

#         for i in range(attemp_count):
#             logger.debug(f"Пробуем получить карточку: [{wb_client.account_name}|{nm_id=}|attemp={i + 1}/{attemp_count}]...")
#             wb_card = await wb_client.get_card(nm_id=nm_id)

#             if wb_card:
#                 logger.debug(f"Карточка найдена: [{wb_client.account_name}|{nm_id=}|attemp={i + 1}/{attemp_count}].")
#                 break

#             logger.debug(f"Карточка не найдена: [{wb_client.account_name}|{nm_id=}|attemp={i + 1}/{attemp_count}].")
#             if i < attemp_count - 1:
#                 await asyncio.sleep(1)

#         return wb_card

#     async def _update_card_data_dimensions(
#         self,
#         nm_ids: list[int],
#         data: ProductWBSpecificationUpdate,
#         user_id: Optional[int] = None,
#     ) -> None:
#         if not nm_ids:
#             return

#         card_data_map = await self._card_data_repo.get_card_data_by_article_ids(nm_ids)
#         now = datetime.today()
#         to_upsert = []

#         for nm_id in nm_ids:
#             card_data = card_data_map.get(nm_id)

#             if not card_data:
#                 logger.warning(f"card_data не найден для nm_id={nm_id}")
#                 continue

#             to_upsert.append((
#                 nm_id,
#                 card_data.barcode or "",
#                 data.dimensions.height,
#                 data.dimensions.length,
#                 data.dimensions.width,
#                 data.dimensions.weight_brutto,
#                 card_data.subject_name,
#                 now,
#                 card_data.chrt_id,
#                 card_data.wb_name,
#                 card_data.wb_description,
#             ))

#         if to_upsert:
#             await self._card_data_repo.create_card_data(to_upsert, user_id)

#     def _build_final_charcs(
#         self,
#         subject_charcs: list[WBCharc],
#         updates: list[CardCharcsUpdate],
#     ) -> list[CardCharcsUpdate]:
#         updates_map = {c.id: c.value for c in updates}
#         available_ids = {c.id for c in subject_charcs}

#         unknown_ids = [c.id for c in updates if c.id not in available_ids]

#         if unknown_ids:
#             raise ValueError(f"Переданы невалидные для предмета характеристики: {unknown_ids}")

#         result: list[CardCharcsUpdate] = []

#         for charc in subject_charcs:
#             if charc.id in updates_map:
#                 value = updates_map[charc.id]
#                 self._validate_value(charc, value)
#                 result.append(CardCharcsUpdate(id=charc.id, value=value))
#                 continue

#             if charc.required:
#                 raise ValueError(
#                     f"Обязательная характеристика '{charc.name}' не заполнена."
#                 )

#         return result

#     @staticmethod
#     def _validate_value(charc: WBCharc, value):
#         if value is None or value == "":
#             if charc.required:
#                 raise ValueError(
#                     f"Обязательная характеристика '{charc.name}' не заполнена."
#                 )
#             return

#         type_valid, type_msg = ProductWBSpecificationsUpdateService._validate_type(
#             charc.charc_type, value
#         )

#         if not type_valid:
#             raise ValueError(type_msg)

#         if isinstance(value, list):
#             count_valid, count_msg = ProductWBSpecificationsUpdateService._validate_count(
#                 len(value), charc.max_count
#             )

#             if not count_valid:
#                 raise ValueError(count_msg)

#     @staticmethod
#     def _validate_type(expected_type: str, value) -> tuple[bool, str]:
#         type_mapping = {
#             "array_of_str": list,
#             "number": (int, float),
#         }

#         expected_python_type = type_mapping.get(expected_type)

#         if expected_python_type is None:
#             return True, ""

#         if not isinstance(value, expected_python_type):
#             actual_type = type(value).__name__
#             return False, (
#                 f"Неверный тип значения: ожидается {expected_type}, "
#                 f"получено {actual_type}"
#             )

#         if expected_type == "array_of_str" and isinstance(value, list):
#             invalid_items = [v for v in value if not isinstance(v, str)]

#             if invalid_items:
#                 return False, (
#                     f"В списке есть элементы не строкового типа: {invalid_items}"
#                 )

#         return True, ""

#     @staticmethod
#     def _validate_count(actual_count: int, max_count: int) -> tuple[bool, str]:
#         if max_count and actual_count > max_count:
#             return False, (
#                 f"Превышено максимальное количество значений: "
#                 f"{actual_count} из {max_count}"
#             )

#         return True, ""

#     async def _get_vat_charc(self, account: str) -> CardCharcsUpdate:
#         accounts = await self._seller_account_repo.get_list()
#         target = next(
#             (acc for acc in accounts if acc.account_name.strip().lower() == account.strip().lower()),
#             None,
#         )

#         if not target:
#             raise ValueError(f"Аккаунт '{account}' не найден для определения НДС.")

#         vat_value = f"{target.vat_rate}" if isinstance(target.vat_rate, int) else "Без НДС"
#         return CardCharcsUpdate(
#             id=PredefinedWBCharcEnum.VAT,
#             value=[vat_value],
#         )

#     @staticmethod
#     def _get_certificate_chars(charcs: list) -> list[CardCharcsUpdate]:
#         certificate_charcs = []

#         for ch in charcs:
#             if ch.id in CertificationCharсEnum:
#                 certificate_charcs.append(
#                     CardCharcsUpdate(
#                         id=ch.id,
#                         value=ch.value,
#                     )
#                 )

#         return certificate_charcs
