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
        """
        Получить остатки по баркодам на одном складе.
        """
        result  = self.get_amount_from_all_warehouses([warehouse_id], barcodes, step)
        return result

    async def get_amount_from_all_warehouses(
        self,
        warehouse_ids: list[int],
        barcodes: list[str],
        step: int = 1000
    ) -> dict[str, list[dict[str, any]]]:
        """
        Получить остатки по баркодам на нескольких складах.
        """
        all_stocks = []

        async with aiohttp.ClientSession() as session:
            for warehouse_id in warehouse_ids:
                url = self.url.format(warehouse_id)

                for start in range(0, len(barcodes), step):
                    barcodes_part = barcodes[start: start + step]
                    json_data = {"skus": barcodes_part}

                    try:
                        async with session.post(url=url, headers=self.headers, json=json_data) as response:
                            if response.status == 200:
                                response_json = await response.json()
                                stocks = response_json.get("stocks", [])

                                all_stocks.extend(stocks)
                            else:
                                print(f"[{self.account}] Ошибка склада {warehouse_id}: {response.status}")
                    except Exception as e:
                        print(f"[{self.account}] Исключение на складе {warehouse_id}: {e}")
                        continue

        return {self.account: all_stocks}

    async def edit_amount_from_warehouses(self, warehouse_id, edit_barcodes_list, step=1000):
        """
        Отправить обновление остатков на один склад продавца.
        """
        result = await self.edit_amount_on_warehouses([warehouse_id], edit_barcodes_list, step)
        return result.get(warehouse_id, False)

    async def send_stock_update(self, session: aiohttp.ClientSession, url: str, stocks: list[dict]) -> tuple[int, dict]:
        """
        Вспомогательный метод: отправляет запрос на обновление остатков.
        """
        async with session.put(url=url, headers=self.headers, json={"stocks": stocks}) as response:
            status = response.status

            try:
                body = await response.json()
            except:
                body = {}

            return status, body

    async def edit_amount_on_warehouses(self, warehouse_ids: list[int], edit_barcodes_list: list[dict], step: int = 1000) -> dict[int, bool]:
        """
        Отправить обновление остатков на несколько складов.
        """
        results = {}

        async with aiohttp.ClientSession() as session:
            for warehouse_id in warehouse_ids:
                url = self.url.format(warehouse_id)
                stocks = edit_barcodes_list.copy()
                success = False
                max_retries = 3  # на случай, если несколько баркодов невалидны

                for _ in range(max_retries):
                    if not stocks:
                        break

                    all_ok = True

                    for start in range(0, len(stocks), step):
                        batch = stocks[start:start + step]
                        status, body = await self.send_stock_update(session, url, batch)

                        if status == 204:
                            success = True
                        elif status == 429:
                            await asyncio.sleep(65)
                            all_ok = False
                            break
                        elif status > 399 and isinstance(body, list):
                            invalid_skus = set()

                            for error in body:
                                if "data" in error:
                                    for item in error["data"]:
                                        invalid_skus.add(item.get("sku"))

                            if invalid_skus:
                                stocks = [s for s in stocks if s["sku"] not in invalid_skus]
                                all_ok = False
                                break  # выходим из батч-цикла, чтобы повторить со всеми валидными
                        else:
                            print(f"[{self.account}] Склад {warehouse_id}: ошибка {status} - {body}")
                            all_ok = False
                            break

                    if all_ok:
                        break

                results[warehouse_id] = success

        return results


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
