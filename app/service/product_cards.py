import asyncio
from datetime import datetime
import logging
from typing import Optional, Any, AsyncGenerator
import re

from asyncpg import Pool

from app.domain.enums import CardStatusEnum, PredefinedWBCharcEnum
from app.domain.models import (
    AccountProductCard,
    WbCard,
    WBCardCreateRequest,
    DimensionsCreate,
    DimensionsUpdate,
    SizeCreate,
    SizeUpdate,
    CardCharcsCreate,
    CardCharcsUpdate,
    WBCardUpdate,
    WBCardVariantLocal,
    WBCardCreate,
    PriceDiscountResponseModel,
    UpdateStocksQuantityResponseModel,
    DuplicateWBProductCardResponse,
    DuplicateCardToAccountsResponse,
    UpdateWBCardsResponse,
    UploadWBCardsResponse,
    StocksFBSQuantityInDB,
)
from app.repository.article import ArticleRepository
from app.repository.card_status import CardStatusRepository
from app.repository.card_data import CardDataRepository
from app.repository.seller_account import SellerAccountRepository
from app.repository.wb_media import WBMediaRepository
from app.service.price_discount import PriceDiscountService
from app.service.stocks_quantity import StocksQuantityService
from app.service.wb_media import WBMediaService
from app.use_cases.card_use_cases.close_card_use_case import CloseCardUseCase
from app.infrastructure.API.wildberries.content.wb_cards import CardsWBAPI, Card
from app.infrastructure.API.wildberries.content.schemes.card_upload import CardCreate, CardVariant
from app.infrastructure.API.wildberries.content.schemes.card_update import CardUpdate
from app.infrastructure.API.wildberries.content.schemes.card_media import CardMediaUploadByLinks


logger = logging.getLogger(__name__)


class NotCreatedCardError(Exception):
    """Карточка товара не была создана."""


class WildberriesCardsService:
    """Сервис для работы с карточками на WB."""
    def __init__(
        self,
        article_repo: ArticleRepository,
        card_status_repo: CardStatusRepository,
        card_data_repo: CardDataRepository,
        price_discount_service: PriceDiscountService,
        stock_quantity_service: StocksQuantityService,
        seller_account_repo: SellerAccountRepository,
        wb_media_repo: WBMediaRepository,
        wb_media_service: WBMediaService,
        pool: Pool,
    ):
        self.article_repo = article_repo
        self.card_status_repo = card_status_repo
        self.card_data_repo = card_data_repo
        self.price_discount_service = price_discount_service
        self.stock_quantity_service = stock_quantity_service
        self._seller_account_repo = seller_account_repo
        self._wb_media_repo = wb_media_repo
        self._wb_media_service = wb_media_service
        self.pool = pool

    async def duplicate_card(
        self,
        wb_client: CardsWBAPI,
        source_nm_id: int,
        close_old: bool = False,
        user_id: Optional[int] = None,
    ) -> DuplicateWBProductCardResponse:
        """
        Создать дубликат карточки.
        Если close_old=True, то карточка-источник будет закрыта.
        """
        original_card = await wb_client.get_card(nm_id=source_nm_id)
        if not original_card:
            raise ValueError(f"Карточка товара [{wb_client.account_name}:{source_nm_id}] не найдена")
        return await self._duplicate(
            source_wb_card=original_card,
            source_wb_client=wb_client,
            target_wb_client=wb_client,
            sync_stocks=False,
            close_old=close_old,
            user_id=user_id,
        )

    async def duplicate_card_to_accounts(
        self,
        source_wb_client: CardsWBAPI,
        target_wb_clients: list[CardsWBAPI],
        source_nm_id: int,
        user_id: Optional[int] = None,
    ) -> DuplicateCardToAccountsResponse:
        """Создать дубликаты карточки на других аккаунтах."""
        original_card = await source_wb_client.get_card(nm_id=source_nm_id)
        if not original_card:
            raise ValueError(f"Карточка товара [{source_wb_client.account_name}:{source_nm_id}] не найдена")

        tasks = [
            self._duplicate(
                source_wb_card=original_card,
                source_wb_client=source_wb_client,
                target_wb_client=target_client,
                sync_stocks=False,
                close_old=False,
                user_id=user_id,
            )
            for target_client in target_wb_clients
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results: DuplicateWBProductCardResponse = []
        errors = []

        for res in results:
            if isinstance(res, Exception):
                error_message = "Создание дубликата карточки nm_id={0} на другой аккаунт завершилось ошибкой: {1}"
                logger.exception(error_message.format(source_nm_id, res))
                errors.append(error_message.format(source_nm_id, str(res)))
                continue

            valid_results.append(res)

        if len(valid_results) != len(target_wb_clients) and valid_results:
            success_execute = "partial"
        elif not valid_results:
            success_execute = "false"
        else:
            success_execute = "true"

        return DuplicateCardToAccountsResponse(
            source_card=AccountProductCard(
                account=source_wb_client.account_name,
                nm_id=original_card.nm_id,
                vendor_code=original_card.vendor_code,
            ),
            new_cards=[
                item.new_card
                for item in valid_results
            ],
            success=success_execute,
            errors=errors
        )

    async def _duplicate(
        self,
        *,
        source_wb_card: WbCard,
        source_wb_client: CardsWBAPI,
        target_wb_client: CardsWBAPI,
        sync_stocks: bool = False,
        close_old: bool = False,
        user_id: Optional[int] = None,
    ) -> dict[str, any]:
        """Создать дубликат карточки. Если close_old, то карточка-источник будет закрыта."""
        logger.info(f"Начинаем создание дубликата карточки [{source_wb_client.account_name}|{source_wb_card.nm_id}] в аккаунте: {target_wb_client.account_name}...")

        # Валидация и получение исходных данных
        old_card_db = await self.article_repo.get_article_by_nm_id_and_account(source_wb_card.nm_id, source_wb_client.account_name)

        if not old_card_db:
            raise ValueError(f"Карта с nm_id={source_wb_card.nm_id} не найдена в учетной записи {source_wb_client.account_name}")

        if old_card_db["vendor_code"] != source_wb_card.vendor_code:
            raise ValueError("Несоответствие vendor_code между базой данных и WB.")

        # Подготовка данных для новой карточки
        creation_payload = await self._build_creation_payload(
            wb_card=source_wb_card,
            local_vendor_code=old_card_db["local_vendor_code"],
            account=target_wb_client.account_name,
        )
        try:
            # Создание на WB и валидация
            upload_result = await self.create_cards_from_request(
                wb_client=target_wb_client,
                creation_requests=[creation_payload],
                user_id=user_id,
            )

            new_card_wb: Optional[WbCard] = None

            if upload_result:
                created = upload_result.created

                for new_nm_id in created:
                    for _ in range(3):
                        logger.info(f"Пробуем получить карточку [{target_wb_client.account_name}:{new_nm_id}]...")
                        new_card_wb = await self.get_card_info(wb_client=target_wb_client, nm_id=new_nm_id)
                        
                        if new_card_wb:
                            break

                    if not new_card_wb:
                        await self._delete_article(new_nm_id, target_wb_client.account_name)
                        logger.warning(f"Не удалось получить новую карточку после создания в аккаунте {target_wb_client.account_name} ")
                        raise NotCreatedCardError

            if not new_card_wb:
                raise NotCreatedCardError
        except NotCreatedCardError:
            raise NotCreatedCardError(
                f"Не удалось создать дубликат карточки [{source_wb_client.account_name}|{source_wb_card.nm_id}]" 
                f"в учетной записи {target_wb_client.account_name}. {". ".join(upload_result.errors)}"
            )

        logger.info(
            f"Создан дубликат [{target_wb_client.account_name}:{new_card_wb.nm_id}]. "
            "Синхронизируем медиа, цены и остатки..."
        )

        async with asyncio.TaskGroup() as group:
            # Синхронизация медиа
            group.create_task(self._sync_media(
                source_wb_client=source_wb_client,
                target_wb_client=target_wb_client,
                source_wb_card=source_wb_card,
                target_wb_card=new_card_wb,
            ))

            # Синхронизация цен
            group.create_task(self._sync_price_discount(
                source_wb_client=source_wb_client,
                target_wb_client=target_wb_client,
                source_wb_card=source_wb_card,
                target_wb_card=new_card_wb,
            ))

            # Синхронизация остатков
            if sync_stocks:
                group.create_task(self._sync_stocks(
                source_wb_client=source_wb_client,
                target_wb_client=target_wb_client,
                source_wb_card=source_wb_card,
                target_wb_card=new_card_wb,
            ))

        # Закрытие старой карточки
        try:
            if close_old:
                logger.info(f"Закрываем карточку [{source_wb_client.account_name}:{source_wb_card.nm_id}]")

                await self._close_card(source_wb_card.nm_id, source_wb_client)
                status_data = await self.card_status_repo.get_status_by_nm_and_account([(source_wb_card.nm_id, source_wb_client.account_name)])
                current_status = status_data.get((source_wb_card.nm_id, source_wb_client.account_name))
                await self._update_fbs_stocks(amount=0, wb_client=source_wb_client, wb_card=source_wb_card)
                if current_status == CardStatusEnum.closing_pending or current_status == CardStatusEnum.closed:
                    logger.info(f"Карточка [{source_wb_client.account_name}:{source_wb_card.nm_id}] закрыта.")
                else:
                    logger.warning(f"Карточка [{source_wb_client.account_name}:{source_wb_card.nm_id}] не закрыта. {close_old=}")
        except Exception as e:
            logger.exception(f"Ошибка во время передачи карточки на закрытие [{target_wb_client.account_name}:{new_card_wb.nm_id}]: {e}")

        return DuplicateWBProductCardResponse(
            source_card=AccountProductCard(
                account=source_wb_client.account_name,
                nm_id=source_wb_card.nm_id,
                vendor_code=source_wb_card.vendor_code,
            ),
            new_card=AccountProductCard(
                account=target_wb_client.account_name,
                nm_id=new_card_wb.nm_id,
                vendor_code=new_card_wb.vendor_code,
            ),
            close_source=close_old
        )

    async def create_cards_from_request(
        self,
        wb_client: CardsWBAPI,
        creation_requests: list[WBCardCreateRequest],
        user_id: Optional[int] = None,
    ) -> UploadWBCardsResponse:
        """Создать новые карточки на WB."""
        logger.info("Начинаем создание карточек на WB...")

        errors = []
        created_cards: list[WbCard] = []
        updated_nm_ids = set()
        cards_to_upload: list[WBCardCreate] = []

        for card_to_create in creation_requests:
            variants = []

            for variant in card_to_create.variants:
                target_vendor_code = await self._generate_target_vendor_code(
                    local_vendor_code=variant.local_vendor_code,
                    wb_client=wb_client,
                )

                existing_card = await wb_client.get_card(vendor_code=target_vendor_code)

                if not existing_card:
                    variants.append(CardVariant(**variant.model_dump(), vendor_code=target_vendor_code))
                    continue

                # Если карточка существует, то актуализируем данные
                logger.warning(
                    f"Карточка [{wb_client.account_name}:{target_vendor_code}] уже существует в ЛК. Обновляем данные."
                )

                # сохраняем карточку в бд
                await self._add_new_card_to_db(existing_card, wb_client.account_name)
                await self._set_card_status([existing_card.nm_id], wb_client.account_name, CardStatusEnum.new)
                await self._update_card_data_in_db([existing_card], user_id=user_id)

                update_result = await self.update_cards_from_request(
                    wb_client=wb_client,
                    user_id=user_id,
                    update_cards=[
                        WBCardUpdate(
                            nm_id=existing_card.nm_id,
                            vendor_code=existing_card.vendor_code,
                            brand=variant.brand or "",
                            title=variant.title or "",
                            description=variant.description or "",
                            dimensions=DimensionsUpdate(
                                width=variant.dimensions.width,
                                height=variant.dimensions.height,
                                length=variant.dimensions.length,
                                weight_brutto=variant.dimensions.weight_brutto,
                            ),
                            characteristics=[CardCharcsUpdate(
                                id=ch.id,
                                value=ch.value
                            ) for ch in variant.characteristics],
                            sizes=[SizeUpdate(
                                chrt_id=sz.chrt_id,
                                tech_size=sz.tech_size,
                                wb_size=sz.wb_size,
                                price=sz.price,
                                skus=sz.skus
                            ) for sz in existing_card.sizes],
                        )
                    ]
                )

                updated_card = await self.get_card_info(
                    wb_client=wb_client,
                    nm_id=update_result.updated[0]
                )

                if updated_card:
                    updated_nm_ids.add(updated_card.nm_id)
                    created_cards.append(updated_card)
            if variants:
                cards_to_upload.append(
                    CardCreate(
                        subject_id=card_to_create.subject_id,
                        variants=variants
                    )
                )

        if cards_to_upload:
            all_new_vendor_codes = set()
            for card in cards_to_upload:
                for variant in card.variants:
                    all_new_vendor_codes.add(variant.vendor_code)

            found_errors = await wb_client.get_uncreated_cards(all_new_vendor_codes)
            await wb_client.upload_cards(cards_to_upload)

            for card in cards_to_upload:
                for variant in card.variants:
                    all_vc_errors = found_errors.get(variant.vendor_code)
                    last_error_batch_id = None
                    if all_vc_errors:
                        last_error_batch_id = all_vc_errors[0]["uuid"]

                    created_card_result = await self._wait_for_card_creation(
                        wb_client=wb_client,
                        vendor_code=variant.vendor_code,
                        last_error_batch_id=last_error_batch_id,
                    )
                    created_card = created_card_result["card"]

                    if created_card:
                        created_cards.append(created_card)
                    else:
                        error_msg = f"Ошибка при создании карточки {variant.vendor_code}: {created_card_result["error"]}"
                        logger.error(error_msg)
                        errors.append(error_msg)

        nm_ids = []

        if created_cards:
            for card in created_cards:
                nm_ids.append(card.nm_id)
                
                if card.nm_id not in updated_nm_ids:
                    await self._add_new_card_to_db(card, wb_client.account_name)

            await self._set_card_status(nm_ids, wb_client.account_name, CardStatusEnum.new)
            await self._update_card_data_in_db(created_cards, user_id=user_id)

        return UploadWBCardsResponse(
            account=wb_client.account_name,
            created=nm_ids,
            errors=errors,
        )

    async def update_cards_from_request(
        self,
        wb_client: CardsWBAPI,
        update_cards: list[WBCardUpdate],
        user_id: Optional[int] = None,
    ) -> UpdateWBCardsResponse:
        """Обновить карточки на WB."""
        logger.info("Начинаем обновление карточек на WB...")

        if not update_cards:
            raise ValueError("Пустой запрос.")

        updated_cards: list[WbCard] = []
        errors = []

        all_vc_to_update = set()

        for update_data in update_cards:
            all_vc_to_update.add(update_data.vendor_code)

        try:
            found_errors = await wb_client.get_uncreated_cards(all_vc_to_update)
            await wb_client.update_cards([CardUpdate(**item.model_dump()) for item in update_cards])

            async for update_result in self._fetch_updated_result(
                wb_client=wb_client,
                update_cards=update_cards,
                errors_before_update_operation=found_errors,
            ):
                if isinstance(update_result, (WbCard, Card)):
                    updated_cards.append(update_result)
                    await self.article_repo.update_article(
                        nm_id=update_result.nm_id,
                        account=wb_client.account_name,
                        vendor_code=update_result.vendor_code
                    )
                elif isinstance(update_result, str):
                    errors.append(update_result)

            if updated_cards:
                await self._update_card_data_in_db(updated_cards, user_id=user_id)
        except Exception as e:
            error_msg = f"Ошибка обновления карточек учетной записи {wb_client.account_name}: {e}"
            logger.exception(error_msg)
            raise e

        return UpdateWBCardsResponse(
            account=wb_client.account_name,
            updated=[card.nm_id for card in updated_cards],
            errors=errors,
        )

    async def _fetch_updated_result(
        self,
        wb_client: CardsWBAPI,
        update_cards: list[WBCardUpdate],
        errors_before_update_operation: dict[str, Any],
    ) -> AsyncGenerator[str | WbCard | Card, None]:
        all_vc_to_update = {card.vendor_code for card in update_cards}
        all_nm_ids = {card.nm_id for card in update_cards}
        last_mismatch_map = {}

        for _ in range(20):
            last_errors_vcs = await wb_client.get_uncreated_cards(all_vc_to_update)

            for update_data in update_cards:
                if update_data.nm_id not in all_nm_ids:
                    continue

                logger.info(f"Проверка обновления карточки [{wb_client.account_name}:{update_data.nm_id}].")
                old_vc_errors = errors_before_update_operation.get(update_data.vendor_code)
                last_error_batch_id = old_vc_errors[0]["uuid"] if old_vc_errors else None

                card = await wb_client.get_card(nm_id=update_data.nm_id)

                if not card or not card.updated_at:
                    not_card_error = f"Карточки [{wb_client.account_name}:{update_data.nm_id}] нет в ЛК."
                    yield not_card_error
                    all_nm_ids.remove(update_data.nm_id)
                    continue

                check_update_message = self._is_wb_card_updated_correctly(
                    card=card,
                    update=update_data,
                )

                if check_update_message is None:
                    logger.info(f"Карточка [{wb_client.account_name}:{card.nm_id}] обновлена.")
                    yield card
                    all_nm_ids.remove(update_data.nm_id)
                    continue
                else:
                    logger.info(f"Карточка [{wb_client.account_name}:{card.nm_id}] не обновлена.")
                    last_mismatch_map[update_data.nm_id] = check_update_message

                error_data = last_errors_vcs.get(card.vendor_code)

                if error_data:
                    last_errors = error_data[0]
                    
                    if last_error_batch_id and last_error_batch_id != last_errors["uuid"] or last_error_batch_id is None:
                        errors_message = "\n".join(last_errors["errors"])
                        logger.warning(f"При обновлении карточки [{wb_client.account_name}:{update_data.nm_id}] получена ошибка: {errors_message}.")
                        yield errors_message
                        all_nm_ids.remove(update_data.nm_id)
                        continue

                logger.info(f"При обновлении карточки [{wb_client.account_name}:{card.nm_id}] ошибок не найдено.")

        if all_nm_ids:
            error_message = (
                "Закончились попытки проверить обновление карточек "
                f"[{wb_client.account_name}:\n{";\n".join(f"{nm} - {last_mismatch_map.get(nm, "нет сообщения.")}" for nm in all_nm_ids)}]"
            )
            logger.warning(error_message)
            yield error_message


    async def get_card_info(
        self,
        wb_client: CardsWBAPI,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None
    ) -> Optional[WbCard]:
        """Получить информацию о карточке с WB."""
        logger.info(f"Поиск карточки товара {nm_id=}, {vendor_code=} в аккаунте {wb_client.account_name}...")
        return await wb_client.get_card(nm_id=nm_id, vendor_code=vendor_code)

    async def get_trashed_card_info(
        self,
        wb_client: CardsWBAPI,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None
    ) -> Optional[WbCard]:
        """Получить информацию о карточке с WB из корзины."""
        logger.info(f"Поиск карточки товара {nm_id=}, {vendor_code=} в корзине аккаунта {wb_client.account_name}...")
        return await wb_client.get_trashed_card(nm_id=nm_id, vendor_code=vendor_code)

    def _is_wb_card_updated_correctly(self, card: WbCard, update: WBCardUpdate) -> str | None:
        """Проверить, что данные карточки соответствую переданным на обновление."""
        if card.nm_id != update.nm_id:
            message = "Проверка обновления карты: несоответствие nm_id."
            logger.debug(message)
            return message

        if card.vendor_code != update.vendor_code:
            message = "Проверка обновления карты: несоответствие vendor_code."
            logger.debug(message)
            return message

        if update.brand:
            if card.brand != update.brand:
                message = "Проверка обновления карты: несоответствие brand."
                logger.debug(message)
                return message
        else:
            if card.brand:
                message = "Проверка обновления карты: brand должен быть пустым."
                logger.debug(message)
                return message

        if (card.title or update.title) and card.title != update.title:
            message = "Проверка обновления карты: несоответствие title."
            logger.debug(message)
            return message

        if (card.description or update.description) and card.description != update.description:
            message = "Проверка обновления карты: несоответствие description."
            logger.debug(message)
            return message

        if (
            card.dimensions.width != update.dimensions.width
            or card.dimensions.height != update.dimensions.height
            or card.dimensions.length != update.dimensions.length
            or abs(card.dimensions.weight_brutto - update.dimensions.weight_brutto) > 1e-6
        ):
            message = "Проверка обновления карты: несоответствие dimensions."
            logger.debug(message)
            return message

        if len(card.characteristics) != len(update.characteristics):
            message = "Проверка обновления карты: несоответствие кол-ва characteristics."
            logger.debug(message)
            return message

        card_charcs_by_id = {c.id: c for c in card.characteristics}

        for upd_char in update.characteristics:
            if upd_char.id not in card_charcs_by_id:
                message = "Проверка обновления карты: не найден characteristic id."
                logger.debug(message)
                return message

            card_char = card_charcs_by_id[upd_char.id]

            if card_char.value != upd_char.value:
                message = "Проверка обновления карты: несоответствие значения characteristic."
                logger.debug(message)
                return message

        card_sizes = card.sizes
        update_sizes = update.sizes

        card_by_chrt = {s.chrt_id: s for s in card_sizes}

        size_updates: list[SizeUpdate] = []
        size_creates: list[SizeCreate] = []

        for sz in update_sizes:
            if isinstance(sz, SizeUpdate):
                size_updates.append(sz)
            elif isinstance(sz, SizeCreate):
                size_creates.append(sz)
            else:
                message = "Проверка обновления карты: неизвестный тип size."
                logger.debug(message)
                return message

        for upd in size_updates:
            if upd.chrt_id not in card_by_chrt:
                message = "Проверка обновления карты: не найден size chrt_id."
                logger.debug(message)
                return message

            card_sz = card_by_chrt[upd.chrt_id]

            if (
                card_sz.tech_size != upd.tech_size
                or card_sz.wb_size != upd.wb_size
                or card_sz.price != upd.price
                or set(card_sz.skus) != set(upd.skus)
            ):
                message = "Проверка обновления карты: несоответствие значения size."
                logger.debug(message)
                return message

        card_by_tech_wb = set()

        for sz in card_sizes:
            key = (sz.tech_size, sz.wb_size)
            card_by_tech_wb.add(key)

        for create in size_creates:
            key = (create.tech_size, create.wb_size)

            if key not in card_by_tech_wb:
                message = "Проверка обновления карты: size create не найден."
                logger.debug(message)
                return message

        if len(card_sizes) != len(size_updates) + len(size_creates):
            message = "Проверка обновления карты: несоответствие кол-ва sizes."
            logger.debug(message)
            return message

    async def _wait_for_card_creation(
        self,
        wb_client: CardsWBAPI,
        vendor_code: str,
        last_error_batch_id: Optional[str] = None
    ) -> dict[str, any]:
        """Проверить, создалась ли карточка."""
        result = {
            "vendor_code": vendor_code,
            "card": None,
            "error": None
        }

        for _ in range(20):
            logger.info(f"Проверка наличия карточки [{wb_client.account_name}:{vendor_code}].")
            card = await wb_client.get_card(vendor_code=vendor_code)

            if card:
                logger.info(f"Созданная карточка [{wb_client.account_name}:{vendor_code}] найдена.")
                result["card"] = card
                return result

            logger.info(f"Созданная карточка [{wb_client.account_name}:{vendor_code}] не найдена.")

            errors_message = await self._check_uncrated_card(
                wb_client=wb_client,
                vendor_code=vendor_code,
                last_error_batch_id=last_error_batch_id
            )

            if errors_message:
                logger.info(f"При создании карточки [{wb_client.account_name}:{vendor_code}] получена ошибка: {errors_message}.")
                result["error"] = errors_message
                return result

            logger.info(f"При создании карточки [{wb_client.account_name}:{vendor_code}] ошибок не найдено.")
            await asyncio.sleep(3)

        error_message = f"Закончились попытки проверить создание карточки [{wb_client.account_name}:{vendor_code}]"
        logger.warning(error_message)
        result["error"] = error_message

        return result

    async def _check_uncrated_card(
        self,
        wb_client: CardsWBAPI,
        vendor_code: str,
        last_error_batch_id: Optional[str] = None
    )-> Optional[dict[str, str]]:
        """Найти последние ошибки при создании/обновлении карточки товара."""
        error_data = await wb_client.get_uncreated_card(vendor_code)

        if error_data:
            last_errors = error_data[0]
            if last_error_batch_id and last_error_batch_id != last_errors["uuid"] or last_error_batch_id is None:
                logger.info(f"Для карточки [{wb_client.account_name}:{vendor_code}] найдены ошибки: {last_errors["errors"]}.")
                return {
                    "batch_id": last_errors["uuid"],
                    "error": "\n".join(last_errors["errors"])
                }

        logger.info(f"Для карточки [{wb_client.account_name}:{vendor_code}] ошибок не найдено.")

    async def _generate_target_vendor_code(
        self,
        wb_client: CardsWBAPI,
        local_vendor_code: str,
    ) -> str:
        """Генерирует детерминированный новый свободный vendor_code."""
        # vendor_code уже существующие в article
        existing_vendor_codes = await self.article_repo.get_vendor_codes_by_local_and_account(
            account=wb_client.account_name,
            local_vendor_code=local_vendor_code,
        )

        if local_vendor_code not in existing_vendor_codes:
            trashed_card = await self.get_trashed_card_info(
                wb_client=wb_client,
                vendor_code=local_vendor_code
            )

            if trashed_card is None:
                return local_vendor_code

        index = 1

        while True:
            suffix = "d" if index == 1 else f"d{index}"
            candidate = f"{local_vendor_code}{suffix}"

            if candidate not in existing_vendor_codes:
                trashed_card = await self.get_trashed_card_info(
                    wb_client=wb_client,
                    vendor_code=candidate
                )

                if trashed_card is None:
                    return candidate

            index += 1

    async def _build_creation_payload(
        self,
        wb_card: WbCard,
        local_vendor_code: str,
        account: str,
    ) -> WBCardCreateRequest:
        """Получить объект с данными из переданных от клиента для создания карточки."""
        logger.info("Собираем данные для создания карточек в объект WBCardCreateRequest...")
        sizes = wb_card.sizes or []
        dimensions = wb_card.dimensions or []
        characteristics = wb_card.characteristics or []

        for item in characteristics:
            if item.id == PredefinedWBCharcEnum.VAT:
                vat_value = await self._get_vat(account)
                item.value = vat_value

        new_card = WBCardVariantLocal(
            local_vendor_code=local_vendor_code,
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
            variants=[new_card]
        )

    async def _add_new_card_to_db(self, new_card: WbCard, account: str) -> None:
        """Добавить новую карточку в БД."""
        logger.info(f"Добавляем карточку товара [{account}:{new_card.nm_id}] в article...")
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

    async def _update_card_data_in_db(self, cards: list[WbCard], user_id: Optional[int] = None) -> None:
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
                card.sizes[0].chrt_id,
                card.title,
                card.description,
            )

            data_to_update.append(card_data)

        await self.card_data_repo.create_card_data(data_to_update, user_id=user_id)

    async def _add_media_from_links(
        self,
        nm_id: int,
        links: CardMediaUploadByLinks,
        wb_client: CardsWBAPI
    ) -> bool:
        """
        Добавить фото/видео к карточке товара по ссылкам.

        Передавать нужно весь список ссылок, включая те, что уже есть.
        Порядок фото зависит от порядка ссылок.
        Ссылка на видео может быть в любом месте списка.
        """
        logger.info(f"Загружаем медиа для карточки товара [{wb_client.account_name}:{nm_id}]...")
        await wb_client.upload_media_by_links(links)

    async def _get_card_price_discount(self, nm_id: int, wb_client: CardsWBAPI) -> dict[str, int]:
        """Получить цену и скидку для карточки товара."""
        logger.info(f"Получаем цены для карточки товара [{wb_client.account_name}:{nm_id}]...")
        return await self.price_discount_service.get_price_and_discount_by_nm_id(
            nm_id=nm_id, account=wb_client.account_name
        )

    async def _get_fbs_stocks(self, nm_id: int) -> int:
        """Получить остатки ФБС для карточки товара."""
        logger.info(f"Получаем остатки ФБС для карточки товара {nm_id}")
        all_stock_qty = await self.stock_quantity_service.get_all_data()
        stock_qty_data = list(filter(lambda x: x.article_id == nm_id, all_stock_qty))

        result = 0

        if stock_qty_data:
            result = stock_qty_data[0].data.get("ФБС", 0)

        return result

    async def _close_card(self, nm_id: int, wb_client: CardsWBAPI) -> None:
        """Закрыть карточку товара."""
        logger.info(f"Закрываем карточку товара {nm_id} для аккаунта {wb_client.account_name}...")
        accounts_data = {wb_client.account_name: [nm_id]}
        card_closer = CloseCardUseCase(self.pool)

        try:
            await card_closer.execute(accounts_data, preview_operation_id=f"after_duplicate_{nm_id}")
        except Exception as e:
            raise Exception(
                detail=f"Ошибка во время закрытия карточки {nm_id}: {e}"
            )

    async def _delete_article(self, nm_id: int, account: str):
        """Удалить карточку из БД."""
        logger.info(f"Удаляем карточку {nm_id} аккаунта {account} из БД.")
        try:
            await self.article_repo.delete_article(nm_id, account)
            logger.info(f"Карточка {nm_id} аккаунта {account} удалена из БД.")
        except Exception as e:
            message = f"Ошибка во время удаления карточки {nm_id} из БД: {e}"
            logger.exception(message)
            raise

    async def _update_price_discount(
        self,
        price_discount_data: dict[str: int],
        wb_client: CardsWBAPI,
        wb_card: WbCard
    ):
        """Обновить цены и скидки карточки."""
        price_data = {
            "update_data": {
                wb_client.account_name.upper(): {
                    "data": [{
                        "nmID": wb_card.nm_id,
                        "price": price_discount_data["price"],
                        "discount": price_discount_data["discount"]
                    }]
                }
            }
        }

        to_price_update = PriceDiscountResponseModel.model_validate(price_data)

        try:
            await self.price_discount_service.update(to_price_update)
        except AttributeError as e:
            # возможно цена была установлена ранее
            new_price_discount = await self._get_card_price_discount(wb_card.nm_id, wb_client)

            if new_price_discount["price"] == price_discount_data["price"] \
                and new_price_discount["discount"] == price_discount_data["discount"]:
                logger.warning(f"Цены для новой карточки [{wb_client.account_name}:{wb_card.nm_id}] уже установлены.")
            else:
                raise Exception(e)

        for _ in range(20):
            new_price_discount = await self._get_card_price_discount(wb_card.nm_id, wb_client)
            price_discount_sync = (
                new_price_discount["price"] == price_discount_data["price"]
                and new_price_discount["discount"] == price_discount_data["discount"]
            )

            if price_discount_sync:
                logger.info(f"Цены для карточки [{wb_client.account_name}:{wb_card.nm_id}] обновлены")
                return
            else:
                logger.info(f"Цены для карточки [{wb_client.account_name}:{wb_card.nm_id}] не обновлены")
                await asyncio.sleep(3)

    async def _update_fbs_stocks(
        self,
        amount: int,
        wb_client: CardsWBAPI,
        wb_card: WbCard
    ):
        """Обновить виртуальные остатки карточки."""

        status_data = await self.card_status_repo.get_status_by_nm_and_account(
            [(wb_card.nm_id, wb_client.account_name)]
        )

        status = status_data.get((wb_card.nm_id, wb_client.account_name), CardStatusEnum.active)

        if status in (CardStatusEnum.closed, CardStatusEnum.closing_pending):
            amount = 0

        target_sku = wb_card.sizes[0].skus[-1]
        update_data = {
            wb_client.account_name: UpdateStocksQuantityResponseModel(
                stocks=[
                    {
                        "sku": target_sku,
                        "amount": amount
                    }
                ]
            )
        }

        await self.stock_quantity_service.edit_stocks_quantity(update_data)

        if amount > 0:
            await self.card_status_repo.update_card_status(
                account=wb_client.account_name,
                nm_ids=[wb_card.nm_id],
                new_status=CardStatusEnum.active,
                from_status=CardStatusEnum.new,
            )

        for _ in range(20):
            get_stocks_result = await self.stock_quantity_service.get_current_stocks_for_account(
                account=wb_client.account_name, skus=[target_sku]
            )

            for _, get_data in get_stocks_result.items():
                current_amount = get_data["stocks"].get(target_sku)

                if amount == current_amount:
                    await self.stock_quantity_service.update_stocks_in_db([StocksFBSQuantityInDB(
                        article_id=wb_card.nm_id,
                        barcode=target_sku,
                        quantity=current_amount,
                    )])
                    logger.info(f"Для карточки [{wb_client.account_name}:{wb_card.nm_id}] остатки обновлены")
                    return

            logger.info(f"Для карточки [{wb_client.account_name}:{wb_card.nm_id}] остатки не обновлены")
            await asyncio.sleep(3)

    async def _get_vat(self, account: str) -> str:
        """Получить значение для характеристики НДС."""
        accounts = await self._seller_account_repo.get_list()
        target = next(
            (acc for acc in accounts if acc.account_name.strip().lower() == account.strip().lower()),
            None,
        )

        if not target:
            raise ValueError(f"Аккаунт '{account}' не найден для определения НДС.")

        return [f"{target.vat_rate}"] if isinstance(target.vat_rate, int) else ["Без НДС"]

    async def _sync_media(
            self,
            source_wb_client: CardsWBAPI,
            target_wb_client: CardsWBAPI,
            source_wb_card: WbCard,
            target_wb_card: WbCard,
    ):
        """Синхронизировать медиа между двумя карточками."""
        try:
            logger.info(f"Синхронизация медиа [{source_wb_client.account_name}{source_wb_card.nm_id}]->[{target_wb_client.account_name}{target_wb_card.nm_id}]...")

            source_cover = await self._wb_media_repo.get_cover_url_of_card(source_wb_card.nm_id)
            source_video = source_wb_card.video
            source_photos = source_wb_card.photos or []

            all_links = []
            all_links.extend((ph["big"] for ph in source_photos))

            if source_video:
                all_links.append(source_video)

            if all_links:
                data_to_upload = CardMediaUploadByLinks(
                    nm_id=target_wb_card.nm_id,
                    data=all_links,
                )

                await self._add_media_from_links(
                    nm_id=target_wb_card.nm_id,
                    wb_client=target_wb_client,
                    links=data_to_upload,
                )

                try:
                    async with asyncio.TaskGroup() as group:
                        if cover:
                            group.create_task(self._wb_media_service._ensure_card_photo_count(
                                wb_client=target_wb_client,
                                nm_id=target_wb_card.nm_id,
                                expected_count=len(source_photos)
                            ))

                        if source_video:
                            group.create_task(self._wb_media_service._ensure_card_video_state(
                                wb_client=target_wb_client,
                                nm_id=target_wb_card.nm_id,
                                has_video=True
                            ))
                except Exception as e:
                    logger.exception(f"Ошибка во время проверки обновления обложки и видео дублированной карточки: [{target_wb_client.account_name}:{target_wb_card.nm_id}] | {e}")
                
                is_updated = False

                for i in range(3):
                    updated_card = await target_wb_client.get_card(target_wb_card.nm_id)

                    if source_video and not updated_card.video:
                        logger.warning(f"При дублировании не обновлено видео. Попытка {i + 1}. [{target_wb_client.account_name}:{target_wb_card.nm_id}]")
                        await asyncio.sleep(5)
                        continue

                    if source_photos and not updated_card.photos:
                        logger.warning(f"При дублировании не обновлены фото. Попытка {i + 1}. [{target_wb_client.account_name}:{target_wb_card.nm_id}]")
                        await asyncio.sleep(5)
                        continue

                    logger.debug(f"Медиа атрибуты карточки обновлены: {target_wb_card.nm_id}")
                    is_updated = True
                    break

                if is_updated:
                    if source_video:
                        video = updated_card.video
                        await self._wb_media_repo.update_video_of_card(
                            article_id=updated_card.nm_id,
                            media_url=video
                        )

                    if source_cover and updated_card.photos:
                        cover = next((ph["big"] for ph in (updated_card.photos)), None)

                        if cover:
                            await self._wb_media_repo.update_cover_of_card(
                                article_id=updated_card.nm_id,
                                media_url=cover
                            )
        except Exception as e:
            logger.exception(f"Ошибка во время синхронизации медиа [{target_wb_client.account_name}:{target_wb_card.nm_id}]: {e}")

    async def _sync_price_discount(
            self,
            source_wb_client: CardsWBAPI,
            target_wb_client: CardsWBAPI,
            source_wb_card: WbCard,
            target_wb_card: WbCard,
    ):
        """Синхронизировать цены между двумя карточками."""
        try:
            logger.info(f"Синхронизация цен [{source_wb_client.account_name}{source_wb_card.nm_id}]->[{target_wb_client.account_name}{target_wb_card.nm_id}]...")
            logger.info(f"Получаем старые цены: [{source_wb_client.account_name}:{source_wb_card.nm_id}]")
            source_price_discount = await self._get_card_price_discount(
                nm_id=source_wb_card.nm_id,
                wb_client=source_wb_client,
            )

            if source_price_discount:
                logger.info(f"Записываем новые цены: [{target_wb_client.account_name}:{target_wb_card.nm_id}]")
                await self._update_price_discount(
                    source_price_discount,
                    target_wb_client,
                    target_wb_card,
                )
        except Exception as e:
            logger.exception(f"Ошибка во время синхронизации цен [{target_wb_client.account_name}:{target_wb_card.nm_id}]: {e}")

    async def _sync_stocks(
            self,
            source_wb_client: CardsWBAPI,
            target_wb_client: CardsWBAPI,
            source_wb_card: WbCard,
            target_wb_card: WbCard,
    ):
        """Синхронизировать виртуальные остатки между двумя карточками."""
        try:
            logger.info(f"Синхронизация остатков [{source_wb_client.account_name}{source_wb_card.nm_id}]->[{target_wb_client.account_name}{target_wb_card.nm_id}]...")
            logger.info(f"Обновляем остатки: [{target_wb_client.account_name}:{target_wb_card.nm_id}]")
            fbs_qty = await self._get_fbs_stocks(source_wb_card.nm_id)
            await self._update_fbs_stocks(
                fbs_qty,
                target_wb_client,
                target_wb_card,
            )
        except Exception as e:
            logger.exception(f"Ошибка во время синхронизации остатков [{target_wb_client.account_name}:{target_wb_card.nm_id}]: {e}")
