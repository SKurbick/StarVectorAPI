import asyncio
import json
import logging
from typing import AsyncGenerator

import aiohttp

logger = logging.getLogger(__name__)


class Wildberries:
    """Base class"""
    pass


class MarketplaceWB:
    """Base class"""
    pass


class AssemblyTasksMarketplaceWB:
    """API складов маркетплейс"""

    def __init__(self, token):
        self.url = "https://marketplace-api.wildberries.ru/api/v3/orders/"

    def get_list_new_assembly_tasks(self, ):
        pass


class SuppliesMarketplaceWB:
    """API складов маркетплейс"""

    pass


class BalancesMarketplaceWB:
    """API складов маркетплейс"""

    pass


class PassesMarketplaceWB:
    """API складов маркетплейс"""

    pass


class DeliveryByTheSellersMPWB:
    """API складов маркетплейс"""

    pass


class LeftoversMarketplace:
    def __init__(self, token, account):
        self.token = token
        self.url = "https://marketplace-api.wildberries.ru/api/v3/stocks/{}"
        self.account = account
        self.headers = {
            "Authorization": self.token,
            'Content-Type': 'application/json'
        }

    async def get_amount_from_warehouses(self, warehouse_id, barcodes, step=1000):
        url = self.url.format(f"{warehouse_id}")
        barcodes_quantity = []
        for start in range(0, len(barcodes), step):
            barcodes_part = barcodes[start: start + step]

            json_data = {
                "skus": barcodes_part
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, headers=self.headers, json=json_data) as response:
                    response_json = await response.json()
                    stocks = response_json["stocks"]
                    barcodes_quantity.extend(stocks)
                    # if len(stocks) > 0:
                    #     for stock in stocks:
                    #         barcodes_quantity.append(
                    #             {
                    #                 "Баркод": stock["sku"],
                    #                 "остаток": stock["amount"]
                    #             }
                    #         )
        return {self.account:barcodes_quantity}

    async def edit_amount_from_warehouses(self, warehouse_id, edit_barcodes_list, step=1000):
        url = self.url.format(f"{warehouse_id}")
        for start in range(0, len(edit_barcodes_list), step):
            barcodes_part = edit_barcodes_list[start: start + step]
            print(barcodes_part)
            json_data = {
                "stocks": barcodes_part
            }
            async with aiohttp.ClientSession() as session:
                async with session.put(url=url, headers=self.headers, json=json_data) as response:
                    if response.status > 399:
                        response_json = await response.json()
                        print(f"Запрос на изменение остатков: {response_json}")
                    else:
                        print(f"Запрос на изменение остатков. Код: {response.status}" )
                        return response.status

class WarehouseMarketplaceWB:
    """API складов маркетплейс"""

    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": self.token,
            'Content-Type': 'application/json'
        }
        self.url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"

    async def get_account_warehouse(self, ):
        for _ in range(5):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=self.url, headers=self.headers) as response:
                        response_json = await response.json()
                        if response.status > 400:
                            await asyncio.sleep(36)
                            continue
                    return response_json
            except Exception as e:
                print(e)


class CardMarketplaceWB:
    BASE_URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"

    def __init__(
        self,
        account_name: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ):
        self.account_name = account_name
        self.api_token = api_token
        self.session = session

    async def _make_request(self, params: dict) -> dict:
        """Один запрос с обработкой ошибок."""
        headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }

        async with self.session.post(self.BASE_URL, headers=headers, json=params) as response:
            if response.status == 429:
                logger.warning(f"[429] {self.account_name} — лимит. Ждём 65 сек...")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=429,
                    message="Too Many Requests"
                )

            if response.status >= 400:
                text = await response.text()
                logger.error(f"[{self.account_name}] Ошибка {response.status}: {text[:300]}")
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=text[:300]
                )

            try:
                data = await response.json()
            except json.JSONDecodeError:
                raw = await response.text()
                logger.error(f"[{self.account_name}] JSON decode error. Raw: {raw[:300]}")
                return {}

            return data

    async def iter_cards(self, limit: int = 100) -> AsyncGenerator[list[dict], None]:
        """
        Асинхронный генератор карточек. Поддерживает пагинацию WB.
        """
        # Ограничение от WB на limit <= 100
        limit = 100 if limit > 100 else limit

        params = {
            "settings": {
                "cursor": {
                    "limit": limit
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }

        while True:
            try:
                data = await self._make_request(params)
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    await asyncio.sleep(65)
                    continue

                raise

            cards = data.get("cards", [])

            if not cards:
                break

            yield cards

            cursor = data.get("cursor", {})

            if not cursor:
                break

            if cursor["total"] < limit:
                break

            params["settings"]["cursor"]["updatedAt"] = cursor["updatedAt"]
            params["settings"]["cursor"]["nmID"] = cursor["nmID"]

            await asyncio.sleep(0.6)

    async def get_barcodes_by_nmid(self, nm_ids: list[int]) -> dict[int, list[str]]:
        """
        Возвращает словарь {nm_id: [barcodes]}.
        Использует генератор iter_cards.
        """
        result: dict[int, list[str]] = {}

        async for cards_batch in self.iter_cards():
            for card in cards_batch:
                nm_id = card.get("nmID")

                if nm_id in nm_ids:
                    barcodes = []

                    for size in card.get("sizes", []):
                        barcodes.extend(size.get("skus", []))

                    result[nm_id] = barcodes

            # если нашли все nm_ids — можно завершать
            if all(nm in result for nm in nm_ids):
                break

        return result
