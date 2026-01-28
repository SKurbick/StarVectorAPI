import asyncio
from collections import defaultdict
import logging
import json
import time
from typing import AsyncGenerator, Optional

import aiohttp

from app.config.settings import get_wb_tokens
from app.domain.models import (
    WbCard,
    Wholesale,
    Dimensions,
    CardCharcs,
    Size,
    Tag,
    WbCardTrashed,
)


logger = logging.getLogger(__name__)


class WBCardsAPIError(Exception):
    """Базовое исключение для ошибок WB API."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class WBCardsRateLimitError(WBCardsAPIError):
    """Ошибка превышения лимитов."""
    pass


class WBCardsNotFoundError(WBCardsAPIError):
    """Ресурс не найден (404)."""
    pass


class CardMarketplaceWB:
    """API WB для работы с карточками товаров."""

    WB_CONTENT_BASE_URL = "https://content-api.wildberries.ru"

    WB_CARDS_UPLOAD = "/content/v2/cards/upload"
    WB_CARDS_UPDATE = "/content/v2/cards/update"
    WB_CARDS_TRASH = "/content/v2/cards/delete/trash"
    WB_CARDS_LIST = "/content/v2/get/cards/list"
    WB_CARDS_TRASH_LIST = "/content/v2/get/cards/trash"
    WB_CARDS_ERROR_LIST = "/content/v2/cards/error/list"
    WB_MEDIA_SAVE = "/content/v3/media/save"

    # Базовый лимит для категории Content
    CONTENT_BASE_INTERVAL = 0.6

    # Переопределения для эндпоинтов
    ENDPOINT_OVERRIDES = {
        WB_CARDS_UPLOAD: 6.0,
        WB_CARDS_UPDATE: 6.0,
        WB_CARDS_ERROR_LIST: 6.0,
    }

    # Запас для избежания предела лимитов
    SAFETY_MARGIN = 1.2

    def __init__(
        self,
        account_name: str,
        api_token: str,
        session: aiohttp.ClientSession,
        base_interval: float = CONTENT_BASE_INTERVAL,
        endpoint_overrides: Optional[dict[str, float]] = ENDPOINT_OVERRIDES,
        safety_margin: float = SAFETY_MARGIN,
    ):
        self.account_name = account_name
        self.api_token = api_token
        self.session = session
        self._safety_margin = safety_margin
        self._base_interval = base_interval
        self._endpoint_overrides = endpoint_overrides

        # Блокировщики запросов
        self._locks = defaultdict(asyncio.Lock)
        # Время последних запросов к энпоинтам
        self._last_request_times = defaultdict(float)

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[dict[str, any]] = None,
        max_retries: int = 3
    ) -> dict[str, any]:
        url = f"{self.WB_CONTENT_BASE_URL}{endpoint}"
        headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }

        # Формируем данные для контроля лимитов
        if endpoint not in self.ENDPOINT_OVERRIDES:
            lock = self._locks[self.WB_CONTENT_BASE_URL]
            raw_interval = self._base_interval
            time_key = self.WB_CONTENT_BASE_URL
        else:
            lock = self._locks[endpoint]
            raw_interval = self._endpoint_overrides.get(endpoint, self._base_interval)
            time_key = endpoint

        interval = raw_interval * self._safety_margin

        for attempt in range(1, max_retries + 1):
            try:
                async with lock:
                    now = time.monotonic()
                    elapsed = now - self._last_request_times[time_key]

                    if elapsed < interval:
                        delay = interval - elapsed
                        logger.debug(f"[{self.account_name}] Задержка ограничения лимита {delay:.2f}с для {endpoint}")
                        await asyncio.sleep(delay)

                    self._last_request_times[time_key] = time.monotonic()

                logger.debug(f"[{self.account_name}] Запрос: {method} {endpoint}, attempt: {attempt}")
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 429:
                        logger.warning(f"[{self.account_name}] Превышен лимит запросов на {endpoint}. Задержка 65c...")
                        await asyncio.sleep(65)
                        continue

                    if response.status == 404:
                        logger.warning(f"[{self.account_name}] Ресурс не найден: {endpoint}, {payload=}")
                        raise WBCardsNotFoundError(f"[{self.account_name}] Ресурс не найден: {endpoint}", status_code=404)

                    if response.status == 400:
                        error_text = await response.json()
                        logger.warning(f"[{self.account_name}] WB API error: {error_text.get("errorText")}, {endpoint=}, {payload=}...")
                        raise WBCardsAPIError(f"[{self.account_name}] WB API error: {error_text.get("errorText")}", status_code=response.status)

                    if 500 <= response.status < 600:
                        wait_time = min(2 ** (attempt - 1), 10)
                        logger.warning(f"[{self.account_name}] Серверная ошибка {response.status} на {endpoint}. Попытка {attempt}/{max_retries}. Ждём {wait_time} сек...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return await self._parse_json_response(response)
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    continue
                raise WBCardsAPIError(f"WB API error: {e.message}", status_code=e.status)
            except aiohttp.ClientError as e:
                raise WBCardsAPIError(f"Network error: {str(e)}")
            except json.JSONDecodeError as e:
                raw = await response.text() if "response" in locals() else ""
                logger.error(f"[{self.account_name}] Ошибка преобразования в JSON {endpoint}: {raw[:300]}")
                raise WBCardsAPIError("Некорректный JSON-ответ от WB.")

        raise WBCardsAPIError(f"Превышено максимальное количество попыток ({max_retries}) для {endpoint}")

    async def _parse_json_response(self, response) -> dict[str, any]:
        try:
            return await response.json()
        except json.JSONDecodeError:
            raw = await response.text()
            logger.error(f"[{self.account_name}] JSON decode error. Raw: {raw[:300]}")
            return {}

    async def upload_cards(self, cards: list[dict[str, any]]) -> dict[str, any]:
        """Создать карточки в личном кабинете."""
        return await self._make_request(self.WB_CARDS_UPLOAD, "POST", payload=cards)

    async def update_cards(self, cards: list[dict[str, any]]) -> dict[str, any]:
        """Обновить карточки в личном кабинете."""
        return await self._make_request(self.WB_CARDS_UPDATE, "POST", payload=cards)

    async def move_to_trash(self, nm_ids: list[int]) -> dict[str, any]:
        """Переместить карточки в корзину."""
        payload = {"nmIDs": nm_ids}
        return await self._make_request(self.WB_CARDS_TRASH, "POST", payload=payload)

    async def upload_media_by_links(self, nm_id: int, links: list[str]) -> dict[str, any]:
        """Загрузить фото/видео к карточке по ссылкам."""
        payload = {"nmId": nm_id, "data": links}
        return await self._make_request(self.WB_MEDIA_SAVE, "POST", payload=payload)

    async def _iter_paginated(
        self,
        endpoint: str,
        payload_template: dict[str, any],
        cursor_key: str = "updatedAt",  # какое поле использовать для курсора
    ) -> AsyncGenerator[list[dict[str, any]], None]:
        """Пагинатор для списков карточек."""
        payload = payload_template.copy()
        limit = min(payload.get("settings", {}).get("cursor", {}).get("limit", 100), 100)
        payload["settings"]["cursor"]["limit"] = limit

        while True:
            response = await self._make_request(endpoint, "POST", payload=payload)
            cards = response.get("cards", [])

            if not cards:
                break

            yield cards

            cursor = response.get("cursor", {})

            if not cursor or cursor.get("total", 0) < limit:
                break

            payload["settings"]["cursor"][cursor_key] = cursor[cursor_key]
            payload["settings"]["cursor"]["nmID"] = cursor["nmID"]

    async def iter_cards(
        self,
        vendor_code: Optional[str] = None,
        nm_id: Optional[int] = None,
        object_id: Optional[int] = None,
        limit: int = 100,
        ascending: bool = False,
        with_photo: int = -1,
    ) -> AsyncGenerator[list[dict[str, any]], None]:
        """Генератор списка созданных карточек."""
        payload = {
            "settings": {
                "cursor": {"limit": limit},
                "filter": {"withPhoto": with_photo},
                "sort": {"ascending": ascending}
            }
        }

        if vendor_code or nm_id:
            payload["settings"]["filter"]["textSearch"] = vendor_code or str(nm_id)

        if object_id:
            payload["settings"]["filter"]["objectIDs"] = [object_id]

        async for cards in self._iter_paginated(self.WB_CARDS_LIST, payload, cursor_key="updatedAt"):
            yield cards

    async def iter_trashed_cards(
        self,
        vendor_code: Optional[str] = None,
        nm_id: Optional[int] = None,
        limit: int = 100,
    ) -> AsyncGenerator[list[dict[str, any]], None]:
        """Генератор списка карточек в корзине."""
        payload = {
            "settings": {
                "cursor": {"limit": limit},
                "sort": {"ascending": False}
            }
        }

        if vendor_code or nm_id:
            payload["settings"]["filter"] = {"textSearch": vendor_code or str(nm_id)}

        async for cards in self._iter_paginated(self.WB_CARDS_TRASH_LIST, payload, cursor_key="trashedAt"):
            yield cards

    async def iter_uncreated_cards(self) -> AsyncGenerator[dict[str, any], None]:
        """Генератор ошибок создания карточек."""
        payload = {
            "cursor": {"limit": 100},
            "order": {"ascending": False},
        }

        has_more = True

        while has_more:
            response = await self._make_request(self.WB_CARDS_ERROR_LIST, "POST", payload=payload)
            data = response.get("data", {})

            if not data:
                break

            cursor = data.get("cursor", {})
            has_more = cursor.get("next", False)
            items = data.get("items", [])

            for item in items:
                yield {
                    "uuid": item["batchUUID"],
                    "errors": item.get("errors", {})
                }

            if has_more:
                payload["cursor"]["updatedAt"] = cursor["updatedAt"]
                payload["cursor"]["batchUUID"] = cursor["batchUUID"]

    async def check_uncreated_cards(self, vendor_codes: set[str]) -> dict[str, any]:
        """Проверить, есть ли ошибки создания по списку артикулов продавца."""
        found_errors = {}

        async for item_errors in self.iter_uncreated_cards():
            batch_uuid = item_errors["uuid"]
            errors = item_errors["errors"]

            for vc, error_info in errors.items():
                if vc in vendor_codes:
                    found_errors.setdefault(vc, []).append({
                        "uuid": batch_uuid,
                        "errors": error_info
                    })

        return found_errors


class WBCardsClient:
    """Клиент для работы с API WB по карточкам товаров."""
    def __init__(self, account, session):
        self.account = account.capitalize()
        self.session = session
        self._client: Optional[CardMarketplaceWB] = None

    async def _get_client(self) -> CardMarketplaceWB:
        if self._client is None:
            tokens = await get_wb_tokens()
            token = tokens.get(self.account)

            if not token:
                raise ValueError(f"Токен не найден для учетной записи: {self.account}")

            self._client = CardMarketplaceWB(
                account_name=self.account,
                api_token=token,
                session=self.session
            )

        return self._client

    async def get_card(
        self,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
    ) -> Optional[WbCard]:
        """Найти карточку товара по nm_id или vendor_code."""
        client = await self._get_client()

        async for cards in client.iter_cards(nm_id=nm_id, vendor_code=vendor_code):
            if cards:
                card = self._parse_wb_card(cards[0])

                if card.nm_id == nm_id or card.vendor_code == vendor_code:
                    return card

        return None

    async def create_cards(self, cards: list[dict[str, any]]) -> dict:
        """Создать карточки товаров в личном кабинете."""
        client = await self._get_client()
        payload = [card.model_dump(by_alias=True, mode="json", exclude_none=True) for card in cards]
        return await client.upload_cards(payload)

    async def update_cards(self, cards: list[dict[str, any]]) -> None:
        """Обновить карточки товаров в личном кабинете."""
        client = await self._get_client()
        payload = [card.model_dump(by_alias=True, mode="json", exclude_none=True) for card in cards]
        await client.update_cards(payload)

    async def move_to_trash(self, nm_id: int) -> bool:
        """Переместить карточку товара в корзину."""
        client = await self._get_client()
        await client.move_to_trash([nm_id])

        for _ in range(3):
            card = await self.get_trashed_card(nm_id=nm_id)

            if card and card.nm_id == nm_id:
                return True

        return False
    
    async def get_trashed_card(
        self,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
    ) -> Optional[WbCard]:
        """Найти карточку товара в корзине по nm_id или vendor_code."""
        client = await self._get_client()

        async for cards in client.iter_trashed_cards(nm_id=nm_id, vendor_code=vendor_code):
            if cards:
                card = self._parse_wb_trashed_card(cards[0])

                if card.nm_id == nm_id or card.vendor_code == vendor_code:
                    return card

        return None

    async def check_uncreated_card(self, vendor_code: str):
        """Найти, есть ли ошибки при создании карточки товара."""
        client = await self._get_client()
        check_result = await client.check_uncreated_cards({vendor_code})
        return check_result.get(vendor_code)

    async def add_media_from_links(self, nm_id, links) -> None:
        """
        Добавить фото/видео к карточке товара по ссылкам.
        
        Передавать нужно весь список ссылок, включая те, что уже есть.
        Порядок фото зависит от порядка ссылок.
        Ссылка на видео может быть в любом месте списка.
        """
        client = await self._get_client()
        await client.upload_media_by_links(nm_id=nm_id, links=links)

    def _parse_wb_trashed_card(self, raw_data: dict) -> WbCardTrashed:
        dimensions = raw_data.get("dimensions", {})
        sizes = raw_data.get("sizes", [])
        characteristics = raw_data.get("characteristics", [])

        return WbCardTrashed(
            nm_id=raw_data.get("nmID"),
            subject_id=raw_data.get("subjectID"),
            subject_name=raw_data.get("subjectName"),
            vendor_code=raw_data.get("vendorCode"),
            dimensions=Dimensions(
                length=dimensions.get("length"),
                width=dimensions.get("width"),
                height=dimensions.get("height"),
                weight_brutto=dimensions.get("weightBrutto"),
                is_valid=dimensions.get("isValid"),
            ),
            characteristics=[
                CardCharcs(
                    id=charc.get("id"),
                    name=charc.get("name"),
                    value=charc.get("value")
                )
                for charc in characteristics
            ],
            sizes=[
                Size(
                    chrt_id=size.get("chrtID"),
                    tech_size=size.get("techSize"),
                    wb_size=size.get("wbSize"),
                    price=size.get("price"),
                    skus=size.get("skus")
                )
                for size in sizes
            ],
            created_at=raw_data.get("createdAt"),
            trashed_at=raw_data.get("trashedAt"),
        )

    def _parse_wb_card(self, raw_data: dict) -> WbCard:
        dimensions = raw_data.get("dimensions", {})
        wholesale = raw_data.get("wholesale")
        sizes = raw_data.get("sizes", [])
        characteristics = raw_data.get("characteristics", [])
        tags = raw_data.get("tags", [])

        return WbCard(
            nm_id=raw_data.get("nmID"),
            imt_id=raw_data.get("imtID"),
            nm_uuid=raw_data.get("nmUUID"),
            subject_id=raw_data.get("subjectID"),
            subject_name=raw_data.get("subjectName"),
            vendor_code=raw_data.get("vendorCode"),
            brand=raw_data.get("brand"),
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            video=raw_data.get("video"),
            wholesale=Wholesale(
                enabled=wholesale.get("enabled"),
                quantum=wholesale.get("quantum")
            ) if wholesale else None,
            need_kiz=raw_data.get("needKiz"),
            photos=raw_data.get("photos"),
            dimensions=Dimensions(
                length=dimensions.get("length"),
                width=dimensions.get("width"),
                height=dimensions.get("height"),
                weight_brutto=dimensions.get("weightBrutto"),
                is_valid=dimensions.get("isValid"),
            ),
            characteristics=[
                CardCharcs(
                    id=charc.get("id"),
                    name=charc.get("name"),
                    value=charc.get("value")
                )
                for charc in characteristics
            ],
            sizes=[
                Size(
                    chrt_id=size.get("chrtID"),
                    tech_size=size.get("techSize"),
                    wb_size=size.get("wbSize"),
                    price=size.get("price"),
                    skus=size.get("skus")
                )
                for size in sizes
            ],
            tags=[
                Tag(
                    id=tag.get("id"),
                    name=tag.get("name"),
                    color=tag.get("color"),
                )
                for tag in tags
            ],
            created_at=raw_data.get("createdAt"),
            updated_at=raw_data.get("updatedAt"),
        )
