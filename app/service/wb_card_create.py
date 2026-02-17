import asyncio
import logging
from typing import Optional

from aiohttp import ClientSession

from app.domain.enums import PredefinedWBCharcEnum
from app.domain.models import (
    WBCardUploadRequest,
    WBCardCreateRequest,
    WBCardVariantLocal,
    CardWBMediaLinksUpdate,
    DimensionsCreate,
    CardCharcsCreate,
)
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI
from app.repository.products_data import ProducsDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_charcs import WBCharcRepository
from app.service.product_cards import WildberriesCardsService
from app.service.wb_media import WBMediaService


logger = logging.getLogger(__name__)


class WBCardCreateService:
    """Сервис для создания карточки товара на WB через Content API."""

    def __init__(
        self,
        products_data_repo: ProducsDataRepository,
        wb_charc_repo: WBCharcRepository,
        seller_account_repo: SellerAccountRepository,
        wb_media_service: WBMediaService,
        wb_cards_service: WildberriesCardsService,
        session: ClientSession,
    ):
        self._products_data_repo = products_data_repo
        self._wb_charc_repo = wb_charc_repo
        self._seller_account_repo = seller_account_repo
        self._wb_cards_service = wb_cards_service
        self._wb_media_service = wb_media_service
        self._session = session

    async def create_card(self, data: WBCardUploadRequest, user_id: Optional[int] = None) -> int:
        """Создать карточку товара на WB."""
        logger.info(f"Начинаем создание карточки для product_id={data.product_id} в аккаунте {data.account}.")

        product_data = await self._products_data_repo.get(data.product_id)

        if not product_data:
            raise ValueError(f"Товар с product_id='{data.product_id}' не найден.")

        if not product_data.wb_subject_id:
            raise ValueError(f"Для product_id='{data.product_id}' не задан subject_id.")

        charcs = await self._wb_charc_repo.get_charcs_by_product_id(data.product_id)
        if not charcs:
            raise ValueError(
                f"Для product_id='{data.product_id}' не найдены характеристики в БД."
            )

        vat_charc = await self._get_vat_charc(data.account)
        characteristics = [
            CardCharcsCreate(id=charc.id, value=charc.value)
            for charc in charcs
            if charc.id != PredefinedWBCharcEnum.VAT
        ]
        characteristics.append(vat_charc)
        dimensions = self._build_dimensions(product_data)
        variant = WBCardCreateRequest(
            subject_id=product_data.wb_subject_id,
            variants=[WBCardVariantLocal(
                brand=product_data.wb_brand or "",
                title=data.name or product_data.name,
                description=data.description or "",
                dimensions=dimensions,
                characteristics=characteristics,
                local_vendor_code=data.product_id,
            )]
        )

        wb_client = CardsWBAPI(session=self._session, account_name=data.account)
        upload_result = await self._wb_cards_service.create_cards_from_request(
            wb_client=wb_client,
            creation_requests=[variant],
            user_id=user_id,
        )

        new_card_nm_id = next((item for item in upload_result.created), None)

        if not new_card_nm_id:
            raise RuntimeError(f"Не удалось создать карточку на WB. errors: {upload_result.errors}")

        card = await wb_client.get_card(new_card_nm_id)

        if not card:
            raise RuntimeError("Не удалось получить созданную карточку из WB.")

        logger.info(f"Карточка vendor_code={card.vendor_code} успешно создана, nm_id={card.nm_id}.")

        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(self._wb_media_service.update_card_media_links(data=CardWBMediaLinksUpdate(
                    photos=[],
                    nm_id=card.nm_id,
                    account=wb_client.account_name,
                    user_id=user_id,
                )))

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
            logger.exception(f"Ошибка во время создания краточки {card.nm_id}: {e}")

        return card.nm_id

    def _build_dimensions(self, product_data) -> DimensionsCreate:
        if (
            product_data.wb_width is None
            or product_data.wb_height is None
            or product_data.wb_length is None
            or product_data.wb_weight_brutto is None
        ):
            raise ValueError(
                f"Для product_id={product_data.product_id} отсутствуют WB-габариты."
            )

        return DimensionsCreate(
            width=product_data.wb_width,
            height=product_data.wb_height,
            length=product_data.wb_length,
            weight_brutto=product_data.wb_weight_brutto,
        )

    async def _get_vat_charc(self, account: str) -> CardCharcsCreate:
        """Получить значение характеристики НДС для аккаунта."""
        accounts = await self._seller_account_repo.get_list()
        target = next(
            (acc for acc in accounts if acc.account_name.strip().lower() == account.strip().lower()),
            None,
        )
        if not target:
            raise ValueError(f"Аккаунт '{account}' не найден для определения НДС.")

        vat_value = f"{target.vat_rate}" if isinstance(target.vat_rate, int) else "Без НДС"
        return CardCharcsCreate(
            id=PredefinedWBCharcEnum.VAT,
            value=[vat_value],
        )
