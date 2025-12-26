import asyncio
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional
import re

from asyncpg import Pool

from app.domain.enums import CardStatusEnum
from app.domain.models import (
    WbCard,
    WBCardCreateRequest,
    DimensionsCreate,
    SizeCreate,
    CardCharcsCreate,
    WBCardUpdate,
    WBCardVariantRequest,
    WBCardVariant,
    WBCardCreate,
    PriceDiscountResponseModel,
    UpdateStocksQuantityResponseModel,
    DuplicateWBProductCardResponse,
    UpdateWBCardsResponse,
    UploadWBCardsResponse,
)
from app.infrastructure.WildberriesAPI.cards import WBCardsClient
from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.repository.card_data import CardDataRepository
from app.service.price_discount import PriceDiscountService
from app.service.stocks_quantity import StocksQuantityService
from app.use_cases.card_use_cases.close_card_use_case import CloseCardUseCase


logger = logging.getLogger(__name__)


class WildberriesCardsService:
    """Сервис для работы с карточками на WB."""
    def __init__(
        self,
        article_repo: ArticleRepository,
        card_status_repo: CardStatusRepository,
        card_data_repo: CardDataRepository,
        price_discount_service: PriceDiscountService,
        stock_quantity_service: StocksQuantityService,
        pool: Pool,
    ):
        self.article_repo = article_repo
        self.card_status_repo = card_status_repo
        self.card_data_repo = card_data_repo
        self.price_discount_service = price_discount_service
        self.stock_quantity_service = stock_quantity_service
        self.pool = pool

    async def duplicate_card(
        self,
        wb_client: WBCardsClient,
        nm_id: int,
        close_old: bool = False
    ) -> dict[str, any]:
        """Создать дубликат карточки. Если close_old, то карточка-источник будет закрыта."""
        logger.info(f"Начинаем создание дубликата карточки {nm_id} в аккаунте {wb_client.account}...")

        # Валидация и получение исходных данных
        old_card_db = await self.article_repo.get_article_by_nm_id_and_account(nm_id, wb_client.account)

        if not old_card_db:
            raise ValueError(f"Карта с nm_id={nm_id} не найдена в учетной записи {wb_client.account}")

        old_card_wb = await wb_client.get_card(nm_id=nm_id)

        if old_card_db["vendor_code"] != old_card_wb.vendor_code:
            raise ValueError("Несоответствие vendor_code между базой данных и WB.")

        # Подготовка данных для новой карточки
        creation_payload = self._build_creation_payload(
            wb_card=old_card_wb,
            local_vendor_code=old_card_db["local_vendor_code"]
        )

        # Создание на WB и валидация
        upload_result = await self.create_cards_from_request(
            wb_client=wb_client,
            creation_requests=[creation_payload]
        )

        new_card_wb: Optional[WbCard] = None

        if upload_result:
            created = upload_result.created

            if created:
                new_card_wb = await self.get_card_info(wb_client=wb_client, nm_id=created[0])

        if not new_card_wb:
            raise RuntimeError(f"Не удалось создать дубликат карточки {nm_id} в учетной записи {wb_client.account}.")

        # Синхронизация медиа
        media_links = []

        if old_card_wb.photos:
            media_links = [
                photo["big"]
                for photo in old_card_wb.photos or []
            ]

        if old_card_wb.video:
            media_links.append(old_card_wb.video)

        if media_links:
            added_media = await self._add_media_from_links(
                nm_id=new_card_wb.nm_id,
                links=media_links,
                wb_client=wb_client,
            )

            if not added_media:
                logging.warning(f"Не удалось проверить добавление медиа для {new_card_wb.nm_id} в учетной записи {wb_client.account}.")

        # Синхронизация цен
        logger.info("Получаем старые цены")
        old_card_price_discount = await self._get_card_price_discount(
            nm_id=old_card_wb.nm_id,
            wb_client=wb_client,
        )

        logger.info("Записываем новые цены")

        if old_card_price_discount:
            price_data = {
                "update_data": {
                    wb_client.account.upper(): {
                        "data": [{
                            "nmID": new_card_wb.nm_id,
                            "price": old_card_price_discount["price"],
                            "discount": old_card_price_discount["discount"]
                        }]
                    }
                }
            }

            to_price_update = PriceDiscountResponseModel.model_validate(price_data)
    
            try:
                await self.price_discount_service.update(to_price_update)
            except AttributeError as e:
                # возможно цена была установлена ранее
                new_card_price_discount = await self._get_card_price_discount(new_card_wb.nm_id, wb_client)

                if new_card_price_discount["price"] == old_card_price_discount["price"] \
                    and new_card_price_discount["discount"] == old_card_price_discount["discount"]:
                    logger.warning(f"Цены для новой карточки {new_card_wb.nm_id} уже установлены.")
                else:
                    raise Exception(e)
            
        new_card_price_discount = await self._get_card_price_discount(new_card_wb.nm_id, wb_client)

        price_discount_sync = (
            new_card_price_discount["price"] == old_card_price_discount["price"]
            and new_card_price_discount["discount"] == old_card_price_discount["discount"]
        )
        # Синхронизация остатков
        fbs_qty = await self._get_fbs_stocks(old_card_wb.nm_id)

        await self.stock_quantity_service.edit_stocks_quantity(
            {
                wb_client.account: UpdateStocksQuantityResponseModel(
                    stocks=[
                        {
                            "sku": new_card_wb.sizes[0].skus[-1],
                            "amount": fbs_qty
                        }
                    ]
                )
            }
        )
        fbs_stock_sinc = fbs_qty == await self._get_fbs_stocks(new_card_wb.nm_id)

        # Закрытие старой карточки
        if close_old:
            await self._close_card(old_card_wb.nm_id, wb_client)

        details = []

        if not added_media:
            details.append("Запрос на добавление фото отправлен успешно. Проверьте наличие фото позже.")
        
        if not price_discount_sync:
            details.append("Запрос на обновление цен и скидок отправлен успешно. Проверьте позже.")
        
        if not fbs_stock_sinc:
            details.append("Запрос на обновление остатков отправлен успешно. Проверьте позже.")

        return DuplicateWBProductCardResponse(
            account=wb_client.account,
            source_card=old_card_wb.nm_id,
            new_card=new_card_wb.nm_id,
            media_sinc=added_media,
            price_discount_sinc=price_discount_sync,
            fbs_stock_sinc=fbs_stock_sinc,
            close_source=close_old,
            details=details,
        )

    async def create_cards_from_request(
        self,
        wb_client: WBCardsClient,
        creation_requests: list[WBCardCreateRequest]
    ) -> UploadWBCardsResponse:
        """Создать новые карточки на WB."""
        logger.info("Начинаем создание карточек на WB...")

        errors = []
        created_cards: list[WbCard] = []
        cards_to_upload: list[WBCardCreate] = []

        for card_create in creation_requests:
            variants = []
            vendor_codes = await self._generate_next_vendor_code(
                local_code=card_create.local_vendor_code,
                account=wb_client.account,
                count=len(card_create.variants)
            )

            for i, variant in enumerate(card_create.variants):
                vendor_code = vendor_codes[i]
                existing_card = await wb_client.get_card(vendor_code=vendor_code)

                if existing_card:
                    logger.warning(f"Карточка с vendor_code {vendor_code} уже существует. Пропускаем.")
                    created_cards.append(existing_card)
                    continue

                variants.append(WBCardVariant(**variant.model_dump(), vendor_code=vendor_code))
            if variants:
                cards_to_upload.append(WBCardCreate(
                    subject_id=card_create.subject_id,
                    variants=variants
                ))

        if cards_to_upload:
            await wb_client.create_cards(cards_to_upload)

            for card in cards_to_upload:
                for variant in card.variants:
                    created_card = await self._wait_for_card_creation(
                        wb_client=wb_client, vendor_code=variant.vendor_code
                    )

                    if created_card:
                        created_cards.append(created_card)
                    else:
                        error_msg = f"Ошибка при создании карточки {variant.vendor_code}"
                        logger.error(error_msg)
                        errors.append(error_msg)

        nm_ids = []

        if created_cards:
            for card in created_cards:
                nm_ids.append(card.nm_id)
                await self._add_new_card_to_db(card, wb_client.account)

            await self._set_card_status(nm_ids, wb_client.account, CardStatusEnum.new)
            await self._update_card_data_in_db(created_cards)

        return UploadWBCardsResponse(
            account=wb_client.account,
            created=nm_ids,
            errors=errors,
        )

    async def update_cards_from_request(
        self,
        wb_client: WBCardsClient,
        update_requests: list[WBCardUpdate],
    ) -> UpdateWBCardsResponse:
        """Обновить карточки на WB."""
        logger.info("Начинаем обновление карточек на WB...")

        if not update_requests:
            raise ValueError("Пустой запрос.")

        updated_cards: list[WbCard] = []
        errors = []

        try:
            await wb_client.update_cards(update_requests)

            all_nms = [card.nm_id for card in update_requests]

            for nm_id in all_nms:   
                updated_card = await self._wait_for_card_updated(wb_client, nm_id)

                if updated_card:
                    updated_cards.append(updated_card)
                    await self.article_repo.update_article(
                        nm_id=updated_card.nm_id,
                        account=wb_client.account,
                        vendor_code=updated_card.vendor_code
                    )
                else:
                    errors.append(f"Обновление не подтверждено для nm_id {nm_id} учетной записи {wb_client.account}")
            await self._update_card_data_in_db(updated_cards)
        except Exception as e:
            error_msg = f"Ошибка обновления карточек учетной записи{wb_client.account}: {e}"
            logger.exception(error_msg)
            raise e

        return UpdateWBCardsResponse(
            account=wb_client.account,
            updated=[card.nm_id for card in updated_cards],
            errors=errors,
        )

    async def move_card_to_trash(
        self,
        wb_client: WBCardsClient,
        nm_id: int
    ) -> bool:
        """
        Переместить карточку в корзину на WB и обновляет статус в БД.
        """
        logger.info(f"Перемещаем карточку {nm_id} в корзину...")
        account = wb_client.account

        card_exists = await wb_client.get_card(nm_id=nm_id)

        if not card_exists:
            trashed_card = await wb_client.get_trashed_card(nm_id=nm_id)

            if not trashed_card:
                raise ValueError(f"Карта {nm_id} не найдена в учетной записи {account}")

        success = await wb_client.move_to_trash(nm_id)
        
        if not success:
            raise RuntimeError(f"Не удалось переместить карту {nm_id} в корзину.")

        await self.card_status_repo.update_card_status(account, [nm_id], CardStatusEnum.trashed)
        return True

    async def get_card_info(
        self,
        wb_client: WBCardsClient,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None
    ) -> Optional[WbCard]:
        """Получить информацию о карточке с WB."""
        logger.info(f"Поиск карточки товара {nm_id=}, {vendor_code=} в аккаунте {wb_client.account}...")
        return await wb_client.get_card(nm_id=nm_id, vendor_code=vendor_code)

    async def get_trashed_card_info(
        self,
        wb_client: WBCardsClient,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None
    ) -> Optional[WbCard]:
        """Получить информацию о карточке с WB из корзины."""
        logger.info(f"Поиск карточки товара {nm_id=}, {vendor_code=} в корзине аккаунта {wb_client.account}...")
        return await wb_client.get_trashed_card(nm_id=nm_id, vendor_code=vendor_code)

    async def _wait_for_card_updated(
        self,
        wb_client: WBCardsClient,
        nm_id: int,
        max_retries: int = 4
    ) -> Optional[WbCard]:
        """Проверить, обновилась ли карточка."""
        for i in range(max_retries):
            logger.info(f"Проверка обновления карточки {nm_id}. Попытка {i+1}")
            card = await wb_client.get_card(nm_id=nm_id)

            if not card or not card.updated_at:
                return None

            now = datetime.now(timezone.utc)
            updated_at = card.updated_at

            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            if updated_at > (now - timedelta(minutes=1)):
                return card

            await asyncio.sleep((i + 1) * 5)

        return None

    async def _wait_for_card_creation(
        self,
        wb_client: WBCardsClient,
        vendor_code: str,
        max_retries=4
    ) -> Optional[WbCard]:
        """Проверить, создалась ли карточка."""
        for i in range(max_retries):
            logger.info(f"Проверка наличия карточки {vendor_code}. Попытка {i+1}")
            card = await wb_client.get_card(vendor_code=vendor_code)

            if card:
                return card

            await asyncio.sleep((i + 1) * 10)

        return None

    async def _generate_next_vendor_code(self, local_code: str, account: str, count: int = 1) -> list[str]:
        """Сгенерировать новые vendor_code на основе local_vendor_code."""
        logger.info(f"Генерируем артикулы продавца для local_vendor_code = {local_code}")
        # Получаем все существующие в БД vendor_code
        existing = await self.article_repo.get_vendor_codes_by_local_and_account(local_code, account)
        base = local_code + "d"
        suffixes = [0]

        # Получаем суффиксы с указанием номера дубликата
        for vc in existing:
            normalize_vc = vc.lower()

            if normalize_vc == local_code:
                continue
            if normalize_vc == base:
                suffixes.append(1)
            elif normalize_vc.startswith(base) and normalize_vc[len(base):].isdigit():
                suffixes.append(int(normalize_vc[len(base):]))

        # Определяем наибольший номер дубликата
        last_num = max(suffixes)

        # Создаем новые vendor_code
        generated_vcs = []

        if local_code not in existing:
            generated_vcs.append(local_code)

        for _ in range(count):

            last_num += 1
            next_vc = base + (str(last_num) if last_num > 1 else "")
            generated_vcs.append(next_vc)

        return generated_vcs

    def _build_creation_payload(
        self,
        wb_card: WbCard,
        local_vendor_code: str
    ) -> WBCardCreateRequest:
        """Получить объект с данными из переданных от клиента для создания карточки."""
        logger.info("Собираем данные для создания карточек в объект WBCardCreateRequest...")
        sizes = wb_card.sizes or []
        dimensions = wb_card.dimensions or []
        characteristics = wb_card.characteristics or []

        new_card = WBCardVariantRequest(
            brand=wb_card.brand,
            title=wb_card.title,
            description=wb_card.description,
            wholesale=wb_card.wholesale,
            dimensions=DimensionsCreate(
                width=dimensions.width,
                length=dimensions.length,
                height=dimensions.height,
                weight_brutto=dimensions.weight_brutto,
            ),
            sizes=[SizeCreate(
                tech_size=size.tech_size,
                wb_size=size.wb_size,
            ) for size in sizes],
            characteristics=[CardCharcsCreate(
                id=charc.id,
                value=charc.value,
            ) for charc in characteristics],
        )

        return WBCardCreateRequest(
            subject_id=wb_card.subject_id,
            local_vendor_code=local_vendor_code,
            variants=[new_card]
        )

    async def _add_new_card_to_db(self, new_card: WbCard, account: str) -> None:
        """Добавить новую карточку в БД."""
        logger.info(f"Добавляем карточку товара {new_card.nm_id} в article...")
        wild_match = re.match(r'^wild(\d+).*$', new_card.vendor_code)
        local_vendor_code = f"wild{wild_match.group(1)}" if wild_match else None

        await self.article_repo.create_article(
            nm_id=new_card.nm_id,
            account=account,
            vendor_code=new_card.vendor_code,
            local_vendor_code=local_vendor_code,
        )

    async def _set_card_status(self, nm_ids: list[int], account: str, status: CardStatusEnum):
        """Обновить статус карточки товара в БД."""
        logger.info(f"Обновляем cтатус карточек товаров на {status}: {nm_ids}")
        await self.card_status_repo.update_card_status(account, nm_ids, status)

    async def _update_card_data_in_db(self, cards: list[WbCard]) -> None:
        """Обновить данные о карточке товара в БД."""
        logger.info(f"Обновляем данные в card_data...")
        data_to_update = []

        for card in cards:
            card_data = (
                card.nm_id,
                card.sizes[0].skus[-1] if card.sizes else "",
                card.dimensions.height,
                card.dimensions.length,
                card.dimensions.width,
                card.dimensions.weight_brutto,
                card.subject_name.capitalize(),
                datetime.today(),
            )

            data_to_update.append(card_data)

        await self.card_data_repo.create_card_data(data_to_update)

    async def _add_media_from_links(
        self,
        nm_id: int,
        links: list[str],
        wb_client: WBCardsClient
    ) -> bool:
        """
        Добавить фото/видео к карточке товара по ссылкам.
        
        Передавать нужно весь список ссылок, включая те, что уже есть.
        Порядок фото зависит от порядка ссылок.
        Ссылка на видео может быть в любом месте списка.
        """
        logger.info(f"Загружаем медиа для карточки товара {nm_id}...")
        await wb_client.add_media_from_links(nm_id=nm_id, links=links)
        await asyncio.sleep(10)

        for i in range(3):
            logger.info(f"Проверка добавления медиа для карточки {nm_id}. Попытка {i+1}")
            card = await wb_client.get_card(nm_id=nm_id)

            if card:
                media_links = []

                if card.photos:
                    media_links = [
                        photo["big"]
                        for photo in card.photos or []
                    ]

                if card.video:
                    media_links.append(card.video)
                
                has_media = len(links) == len(media_links)

                if has_media:
                    return True
            else:
                raise ValueError(f"Карточка {nm_id} не найдена.")

            await asyncio.sleep((i + 1) * 10)

        return False

    async def _get_card_price_discount(self, nm_id: int, wb_client: WBCardsClient) -> dict[str, int]:
        """Получить цену и скидку для карточки товара."""
        logger.info(f"Получаем цены для карточки товара {nm_id}...")
        return await self.price_discount_service.get_price_and_discount_by_nm_id(
            nm_id=nm_id, account=wb_client.account
        )

    async def _get_fbs_stocks(self, nm_id: int) -> int:
        """Получить остатки ФБС для карточки товара."""
        logger.info(f"Получаем остатки ФБС для карточки товара {nm_id}")
        all_stock_qty = await self.stock_quantity_service.get_all_data()
        old_stock_qty = list(filter(lambda x: x.article_id == nm_id, all_stock_qty))

        result = 0

        if old_stock_qty:
            result = old_stock_qty[0].data.get("ФБС", 0)

        return result

    async def _close_card(self, nm_id: int, wb_client: WBCardsClient) -> None:
        """Закрыть карточку товара."""
        logger.info(f"Закрываем карточку товара {nm_id} для аккаунта {wb_client.account}...")
        accounts_data = {wb_client.account: [nm_id]}
        card_closer = CloseCardUseCase(self.pool)

        try:
            await card_closer.execute(accounts_data, preview_operation_id=f"after_duplicate_{nm_id}")
        except Exception as e:
            raise Exception(
                detail=f"Ошибка во время закрытия карточки {nm_id}: {e}"
            )
