import logging
from datetime import datetime
from typing import Optional

from aiohttp import ClientSession

from app.domain.enums import PredefinedWBCharcEnum
from app.domain.models import (
    ProsuctWBSpecificationUpdate,
    ProductCharcInfo,
    CardCharcsUpdate,
    WBCardUpdate,
    DimensionsUpdate,
    SizeUpdate,
)
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI
from app.repository.article import ArticleRepository
from app.repository.card_data import CardDataRepository
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_charcs import WBCharcRepository
from app.service.product_cards import WildberriesCardsService
from app.service.wb_specifications import WBCharcService


logger = logging.getLogger(__name__)


class ProductWBSpecificationsUpdateService:
    """Сервис обновления WB-спецификаций товара."""

    def __init__(
        self,
        products_data_repo: ProducsDataRepository,
        wb_charc_repo: WBCharcRepository,
        seller_account_repo: SellerAccountRepository,
        article_repo: ArticleRepository,
        card_data_repo: CardDataRepository,
        wb_charc_service: WBCharcService,
        wb_cards_service: WildberriesCardsService,
        session: ClientSession,
    ):
        self._products_data_repo = products_data_repo
        self._wb_charc_repo = wb_charc_repo
        self._seller_account_repo = seller_account_repo
        self._article_repo = article_repo
        self._card_data_repo = card_data_repo
        self._wb_charc_service = wb_charc_service
        self._wb_cards_service = wb_cards_service
        self._session = session

    async def update_product_specifications(self, data: ProsuctWBSpecificationUpdate, user_id: Optional[int] = None) -> list[dict]:
        """
        Обновить спецификации товара и все его карточки на WB.
        Возвращает список nm_id обновлённых карточек.
        """
        product_data = await self._products_data_repo.get(data.id)

        if not product_data:
            product_is_exists = await self._product_repo.check_product_exists(data.id)

            if not product_is_exists:
                raise ValueError(f"Товар с id={data.id} не найден.")

            await self._products_data_repo.create(data.id)
            product_data = await self._products_data_repo.get(data.id)

        current_charcs = await self._wb_charc_service.get_product_charcs(data.id)
        final_charcs = self._build_final_charcs(current_charcs, data.characteristics)

        await self._products_data_repo.update_wb_specifications(
            product_id=data.id,
            width=data.dimensions.width,
            height=data.dimensions.height,
            length=data.dimensions.length,
            weight_brutto=data.dimensions.weight_brutto,
            brand=data.brand or None,
            user_id=user_id,
        )

        await self._wb_charc_repo.replace_product_charcs(
            product_id=data.id,
            charcs=final_charcs,
            user_id=user_id,
        )

        articles, _, _ = await self._article_repo.get_articles_by_criteria(
            local_vendor_codes=[data.id]
        )

        if not articles:
            return []

        cards_by_account: dict[str, list[int]] = {}

        for item in articles:
            cards_by_account.setdefault(item["account"], []).append(item["nm_id"])

        updated_cards: list[dict] = []
        errors: list[str] = []

        for account, nm_ids in cards_by_account.items():
            wb_client = CardsWBAPI(account_name=account, session=self._session)
            vat_charc = await self._get_vat_charc(account)
            update_cards: list[WBCardUpdate] = []

            for nm_id in nm_ids:
                wb_card = await wb_client.get_card(nm_id=nm_id)

                if not wb_card:
                    errors.append(f"Карточка nm_id={nm_id} не найдена в аккаунте {account}.")
                    continue

                sizes = [
                    SizeUpdate(
                        chrt_id=size.chrt_id,
                        tech_size=size.tech_size,
                        wb_size=size.wb_size,
                        price=size.price,
                        skus=size.skus,
                    )
                    for size in wb_card.sizes
                ]

                update_cards.append(
                    WBCardUpdate(
                        nm_id=wb_card.nm_id,
                        vendor_code=wb_card.vendor_code,
                        brand=data.brand or "",
                        title=wb_card.title or "",
                        description=wb_card.description or "",
                        dimensions=DimensionsUpdate(
                            width=data.dimensions.width,
                            height=data.dimensions.height,
                            length=data.dimensions.length,
                            weight_brutto=data.dimensions.weight_brutto,
                        ),
                        characteristics=[
                            *final_charcs,
                            vat_charc,
                        ],
                        sizes=sizes,
                    )
                )

            if update_cards:
                result = await self._wb_cards_service.update_cards_from_request(
                    wb_client=wb_client,
                    update_cards=update_cards,
                    user_id=user_id,
                )
                updated_cards.extend(
                    [{"account": account, "nm_id": nm_id} for nm_id in result.updated]
                )
                errors.extend(result.errors)

        if errors:
            raise RuntimeError("; ".join(errors))

        await self._update_card_data_dimensions(
            [item["nm_id"] for item in updated_cards],
            data,
            user_id,
        )

        return updated_cards

    async def _update_card_data_dimensions(
        self,
        nm_ids: list[int],
        data: ProsuctWBSpecificationUpdate,
        user_id: Optional[int] = None,
    ) -> None:
        if not nm_ids:
            return

        card_data_map = await self._card_data_repo.get_card_data_by_article_ids(nm_ids)
        now = datetime.today()
        to_upsert = []

        for nm_id in nm_ids:
            card_data = card_data_map.get(nm_id)

            if not card_data:
                logger.warning(f"card_data не найден для nm_id={nm_id}")
                continue

            to_upsert.append((
                nm_id,
                card_data.barcode or "",
                data.dimensions.height,
                data.dimensions.length,
                data.dimensions.width,
                data.dimensions.weight_brutto,
                card_data.subject_name,
                now,
                card_data.chrt_id,
            ))

        if to_upsert:
            await self._card_data_repo.create_card_data(to_upsert, user_id)

    def _build_final_charcs(
        self,
        current_charcs: list[ProductCharcInfo],
        updates: list[CardCharcsUpdate],
    ) -> list[CardCharcsUpdate]:
        updates_map = {c.id: c.value for c in updates}
        available_ids = {c.id for c in current_charcs}

        unknown_ids = [c.id for c in updates if c.id not in available_ids]

        if unknown_ids:
            raise ValueError(f"Переданы неизвестные характеристики: {unknown_ids}")

        result: list[CardCharcsUpdate] = []

        for charc in current_charcs:
            if charc.id in updates_map:
                value = updates_map[charc.id]
                self._validate_value(charc, value)
                result.append(CardCharcsUpdate(id=charc.id, value=value))
                continue

            if charc.status == "invalid":
                raise ValueError(
                    f"Характеристика '{charc.name}' некорректна и не исправлена."
                )

            if charc.status == "empty":
                if charc.required:
                    raise ValueError(
                        f"Обязательная характеристика '{charc.name}' не заполнена."
                    )
                continue

        return result

    @staticmethod
    def _validate_value(charc: ProductCharcInfo, value):
        if value is None or value == "":
            if charc.required:
                raise ValueError(
                    f"Обязательная характеристика '{charc.name}' не заполнена."
                )
            return

        type_valid, type_msg = ProductWBSpecificationsUpdateService._validate_type(
            charc.charc_type, value
        )

        if not type_valid:
            raise ValueError(type_msg)

        if isinstance(value, list):
            count_valid, count_msg = ProductWBSpecificationsUpdateService._validate_count(
                len(value), charc.max_count
            )

            if not count_valid:
                raise ValueError(count_msg)

    @staticmethod
    def _validate_type(expected_type: str, value) -> tuple[bool, str]:
        type_mapping = {
            "array_of_str": list,
            "number": (int, float),
        }

        expected_python_type = type_mapping.get(expected_type)

        if expected_python_type is None:
            return True, ""

        if not isinstance(value, expected_python_type):
            actual_type = type(value).__name__
            return False, (
                f"Неверный тип значения: ожидается {expected_type}, "
                f"получено {actual_type}"
            )

        if expected_type == "array_of_str" and isinstance(value, list):
            invalid_items = [v for v in value if not isinstance(v, str)]

            if invalid_items:
                return False, (
                    f"В списке есть элементы не строкового типа: {invalid_items}"
                )

        return True, ""

    @staticmethod
    def _validate_count(actual_count: int, max_count: int) -> tuple[bool, str]:
        if max_count and actual_count > max_count:
            return False, (
                f"Превышено максимальное количество значений: "
                f"{actual_count} из {max_count}"
            )

        return True, ""

    async def _get_vat_charc(self, account: str) -> CardCharcsUpdate:
        accounts = await self._seller_account_repo.get_list()
        target = next(
            (acc for acc in accounts if acc.account_name.strip().lower() == account.strip().lower()),
            None,
        )

        if not target:
            raise ValueError(f"Аккаунт '{account}' не найден для определения НДС.")

        vat_value = f"{target.vat_rate}" if isinstance(target.vat_rate, int) else "Без НДС"
        return CardCharcsUpdate(
            id=PredefinedWBCharcEnum.VAT,
            value=[vat_value],
        )
