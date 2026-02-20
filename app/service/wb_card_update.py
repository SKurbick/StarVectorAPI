import asyncio
import logging
from typing import Optional

from aiohttp import ClientSession

from app.domain.models import (
    WBCardSpecificationUpdateRequest,
    SizeUpdate,
    CardCharcsUpdate,
    WBCardUpdate,
    DimensionsUpdate,
)
from app.domain.enums import PredefinedWBCharcEnum
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_charcs import WBCharcRepository
from app.service.product_cards import WildberriesCardsService


logger = logging.getLogger(__name__)


class WBCardUpdateService:
    """Сервис для обновления карточки товара на WB через Content API."""

    def __init__(
        self,
        products_data_repo: ProducsDataRepository,
        wb_charc_repo: WBCharcRepository,
        seller_account_repo: SellerAccountRepository,
        wb_cards_service: WildberriesCardsService,
        session: ClientSession,
    ):
        self._products_data_repo = products_data_repo
        self._wb_charc_repo = wb_charc_repo
        self._seller_account_repo = seller_account_repo
        self._wb_cards_service = wb_cards_service
        self._session = session

    async def update_card(self, data: WBCardSpecificationUpdateRequest, user_id: Optional[int] = None) -> int:
        """Обновить карточку товара на WB."""
        logger.info(f"Начинаем обновление карточки {data.nm_id} в аккаунте {data.account}.")
        product_data = await self._products_data_repo.get(data.product_id)

        if not product_data:
            raise ValueError(f"Товар с product_id='{data.product_id}' не найден.")

        charcs = await self._wb_charc_repo.get_charcs_by_product_id(data.product_id) or []

        wb_client = CardsWBAPI(session=self._session, account_name=data.account)
        card = await wb_client.get_card(nm_id=data.nm_id)

        if not card:
            raise ValueError(
                f"Карточка nm_id={data.nm_id} не найдена в аккаунте {data.account}."
            )

        dimensions = self._build_dimensions(product_data)
        sizes = [
            SizeUpdate(
                chrt_id=size.chrt_id,
                tech_size=size.tech_size,
                wb_size=size.wb_size,
                price=size.price,
                skus=size.skus,
            )
            for size in card.sizes
        ]
        vat_charc = await self._get_vat_charc(data.account)
        characteristics = [
            CardCharcsUpdate(id=charc.id, value=charc.value)
            for charc in charcs
            if charc.id != PredefinedWBCharcEnum.VAT
        ]
        characteristics.append(vat_charc)

        title = data.name
        description = data.description

        update_payload = WBCardUpdate(
            nm_id=data.nm_id,
            vendor_code=card.vendor_code,
            brand=product_data.wb_brand or "",
            title=title,
            description=description,
            dimensions=dimensions,
            characteristics=characteristics,
            sizes=sizes,
        )

        update_result = await self._wb_cards_service.update_cards_from_request(
            wb_client=wb_client,
            update_cards=[update_payload],
            user_id=user_id,
        )

        card_nm_id = next((item for item in update_result.updated), None)

        if not card_nm_id:
            raise RuntimeError(f"Не удалось обновить карточку на WB. errors: {update_result.errors}")

        card = await wb_client.get_card(card_nm_id)

        if not card:
            raise RuntimeError("Не удалось получить обновленную карточку из WB.")

        logger.info(f"Карточка nm_id={card.nm_id} успешно обновлена.")

        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(self._wb_cards_service._update_price_discount(
                    price_discount_data={"price": data.price or 0, "discount": data.price or 0},
                    wb_client=wb_client,
                    wb_card=card,
                ))

                group.create_task(self._wb_cards_service._update_fbs_stocks(
                    amount=data.fbs_stock_quantity or 0,
                    wb_client=wb_client,
                    wb_card=card,
                ))
        except Exception as e:
            logger.exception(f"Ошибка во время обновления краточки {card.nm_id}: {e}")

        logger.info(f"Карточка nm_id={data.nm_id} в аккаунте {data.account} успешно обновлена.")
        return card.nm_id

    def _build_dimensions(self, product_data) -> DimensionsUpdate:
        if (
            product_data.wb_width is None
            or product_data.wb_height is None
            or product_data.wb_length is None
            or product_data.wb_weight_brutto is None
        ):
            raise ValueError(
                f"Для product_id={product_data.product_id} отсутствуют WB-габариты."
            )

        return DimensionsUpdate(
            width=product_data.wb_width,
            height=product_data.wb_height,
            length=product_data.wb_length,
            weight_brutto=product_data.wb_weight_brutto,
        )

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
