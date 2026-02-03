import logging
from typing import Optional, AsyncGenerator

from app.infrastructure.API.wildberries.base.client import HTTPMethod
from app.infrastructure.API.wildberries.content.base import ContentWBAPI
from app.infrastructure.API.wildberries.content.schemes.card import Card
from app.infrastructure.API.wildberries.content.schemes.card_trashed import CardTrashed, CardsToTrash
from app.infrastructure.API.wildberries.content.schemes.card_upload import CardCreate
from app.infrastructure.API.wildberries.content.schemes.card_update import CardUpdate
from app.infrastructure.API.wildberries.content.schemes.card_media import CardMediaUploadByLinks


logger = logging.getLogger(__name__)


class CardsListWBAPI(ContentWBAPI):
    """API-клиент списков карточек товаров WB."""

    WB_CARDS_LIST = "/content/v2/get/cards/list"
    WB_CARDS_TRASH_LIST = "/content/v2/get/cards/trash"

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
            response = await self._make_request(endpoint, HTTPMethod.POST, payload=payload)
            cards = response.get("cards", [])

            if not cards:
                break

            yield cards

            cursor = response.get("cursor", {})

            if not cursor or cursor.get("total", 0) < limit:
                break

            payload["settings"]["cursor"][cursor_key] = cursor[cursor_key]
            payload["settings"]["cursor"]["nmID"] = cursor["nmID"]
        
    async def iter_exists_cards(
        self,
        vendor_code: Optional[str] = None,
        nm_id: Optional[int] = None,
        object_id: Optional[int] = None,
        ascending: bool = False,
        with_photo: int = -1,
    ) -> AsyncGenerator[Card, None]:
        """Генератор списка созданных карточек."""
        payload = {
            "settings": {
                "cursor": {"limit": 100},
                "filter": {"withPhoto": with_photo},
                "sort": {"ascending": ascending}
            }
        }

        if vendor_code and nm_id:
            raise ValueError(
                f"[{self.account_name}] Ошибка при поиске карточек: "
                "Переданы два параметра (можно искать по vendor_code или nm_id)."
            )

        if vendor_code or nm_id:
            payload["settings"]["filter"]["textSearch"] = vendor_code or str(nm_id)

        if object_id:
            payload["settings"]["filter"]["objectIDs"] = [object_id]

        async for cards in self._iter_paginated(self.WB_CARDS_LIST, payload, cursor_key="updatedAt"):
            for card in cards:
                yield Card.model_validate(card)
        
    async def iter_trashed_cards(
        self,
        vendor_code: Optional[str] = None,
        nm_id: Optional[int] = None,
    ) -> AsyncGenerator[list[dict[str, any]], None]:
        """Генератор списка карточек в корзине."""
        payload = {
            "settings": {
                "cursor": {"limit": 100},
                "sort": {"ascending": False}
            }
        }

        if vendor_code or nm_id:
            payload["settings"]["filter"] = {"textSearch": vendor_code or str(nm_id)}

        async for cards in self._iter_paginated(self.WB_CARDS_TRASH_LIST, payload, cursor_key="trashedAt"):
            for card in cards:
                yield CardTrashed.model_validate(card)


class CardsUncreatedWBAPI(ContentWBAPI):
    """API-клиент несозданных карточек товаров WB."""

    WB_CARDS_ERROR_LIST = "/content/v2/cards/error/list"

    async def iter_uncreated_cards(self) -> AsyncGenerator[dict[str, any], None]:
        """Генератор ошибок создания/обновления карточек."""
        payload = {
            "cursor": {"limit": 100},
            "order": {"ascending": False},
        }

        has_more = True

        while has_more:
            response = await self._make_request(self.WB_CARDS_ERROR_LIST, HTTPMethod.POST, payload=payload)
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

    async def get_uncreated_cards(self, vendor_codes: set[str]) -> dict[str, any]:
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

    async def get_uncreated_card(self, vendor_code: str):
        """Найти, есть ли ошибки при создании карточки товара."""
        check_result = await self.get_uncreated_cards({vendor_code})
        return check_result.get(vendor_code)


class CardsMediaWBAPI(ContentWBAPI):
    """API-клиент медиа карточек товаров WB."""

    WB_MEDIA_SAVE = "/content/v3/media/save"

    async def upload_media_by_links(self, card_media: CardMediaUploadByLinks) -> dict[str, any]:
        """Загрузить фото/видео к карточке по ссылкам."""
        payload = card_media.model_dump(by_alias=True, mode="json", exclude_none=True)
        return await self._make_request(self.WB_MEDIA_SAVE, HTTPMethod.POST, payload=payload)


class CardsWBAPI(CardsListWBAPI, CardsUncreatedWBAPI, CardsMediaWBAPI):
    """API-клиент карточек товаров WB."""

    WB_CARDS_UPLOAD = "/content/v2/cards/upload"
    WB_CARDS_UPDATE = "/content/v2/cards/update"
    WB_CARDS_TRASH = "/content/v2/cards/delete/trash"

    async def get_card(
        self,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
    ) -> Optional[Card]:
        """Найти карточку товара по nm_id или vendor_code."""
        async for card in self.iter_exists_cards(nm_id=nm_id, vendor_code=vendor_code):
            if card.nm_id == nm_id or card.vendor_code == vendor_code:
                return card

        return None

    async def upload_cards(self, cards: list[CardCreate]) -> dict[str, any]:
        """Создать карточки в личном кабинете."""
        payload = [card.model_dump(by_alias=True, mode="json", exclude_none=True) for card in cards]
        return await self._make_request(self.WB_CARDS_UPLOAD, HTTPMethod.POST, payload=payload)

    async def update_cards(self, cards: list[CardUpdate]) -> dict[str, any]:
        """Обновить карточки в личном кабинете."""
        payload = [card.model_dump(by_alias=True, mode="json", exclude_none=True) for card in cards]
        return await self._make_request(self.WB_CARDS_UPDATE, HTTPMethod.POST, payload=payload)

    async def move_to_trash(self, cards_to_trash: CardsToTrash) -> dict[str, any]:
        """Переместить карточки в корзину."""
        payload = cards_to_trash.model_dump(by_alias=True, mode="json", exclude_none=True)
        return await self._make_request(self.WB_CARDS_TRASH, HTTPMethod.POST, payload=payload)
