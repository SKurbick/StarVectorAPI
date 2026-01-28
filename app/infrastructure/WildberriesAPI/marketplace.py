import asyncio
import json
import logging
from typing import AsyncGenerator

import aiohttp
from fastapi import HTTPException, status


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

    async def get_amount_from_warehouses(self, warehouse_id, chrt_ids, step=1000):
        """
        Получить остатки по баркодам на одном складе.
        """
        result  = await self.get_amount_from_all_warehouses([warehouse_id], chrt_ids, step)
        return result

    async def get_amount_from_all_warehouses(
        self,
        warehouse_ids: list[int],
        chrt_ids: list[int],
        step: int = 1000
    ) -> dict[str, list[dict[str, any]]]:
        """
        Получить остатки по баркодам на нескольких складах.
        """
        all_stocks = []

        async with aiohttp.ClientSession() as session:
            for warehouse_id in warehouse_ids:
                url = self.url.format(warehouse_id)
                max_retries = 3  # на случай, если несколько chrt_id невалидны или допустимые ошибки от wb

                try:
                    for _ in range(max_retries):
                        all_ok = True

                        for start in range(0, len(chrt_ids), step):
                            chrt_ids_part = chrt_ids[start: start + step]
                            json_data = {"chrtIds": chrt_ids_part}

                            async with session.post(url=url, headers=self.headers, json=json_data) as response:
                                if response.status in (429, 500):
                                    await asyncio.sleep(65)
                                    all_ok = False
                                    break
                                elif response.status == 200:
                                    response_json = await response.json()
                                    stocks = response_json.get("stocks", [])
                                    all_stocks.extend(stocks)
                                else:
                                    print(f"[{self.account}] Ошибка склада {warehouse_id}: {response.status}")

                        if all_ok:
                            break
                except Exception as e:
                        print(f"[{self.account}] Исключение на складе {warehouse_id}: {e}")
                        continue

        return {self.account: all_stocks}

    async def edit_amount_from_warehouses(self, warehouse_id, edit_chrt_ids_list, step=1000):
        """
        Отправить обновление остатков на один склад продавца.
        """
        result = await self.edit_amount_on_warehouses([warehouse_id], edit_chrt_ids_list, step)
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

    async def edit_amount_on_warehouses(self, warehouse_ids: list[int], edit_chrt_ids_list: list[dict], step: int = 1000) -> dict[str, any]:
        """
        Отправить обновление остатков на несколько складов.
        """
        wh_results = {}
        print(edit_chrt_ids_list)
        async with aiohttp.ClientSession() as session:
            for warehouse_id in warehouse_ids:
                url = self.url.format(warehouse_id)
                stocks = edit_chrt_ids_list.copy()
                success = False
                max_retries = 3  # на случай, если несколько chrt_id невалидны или допустимые ошибки от wb
                invalid_chrt_ids = set()
                errors = set()

                for _ in range(max_retries):
                    if not stocks:
                        break

                    all_ok = True

                    for start in range(0, len(stocks), step):
                        batch = stocks[start:start + step]
                        status, body = await self.send_stock_update(session, url, batch)

                        if status == 204:
                            success = True
                        elif status in (429, 500):
                            await asyncio.sleep(65)
                            all_ok = False
                            break
                        elif status > 399 and isinstance(body, list):
                            for error in body:
                                if "data" in error:
                                    for item in error["data"]:
                                        invalid_chrt_ids.add(item.get("chrtId"))

                            if invalid_chrt_ids:
                                stocks = [s for s in stocks if s["chrtId"] not in invalid_chrt_ids]
                                all_ok = False
                                break  # выходим из батч-цикла, чтобы повторить со всеми валидными
                        else:
                            message = f"[{self.account}] Склад {warehouse_id}: ошибка {status} - {body}"
                            print(message)
                            errors.add(message)
                            all_ok = False
                            break

                    if all_ok:
                        break

                wh_results[warehouse_id] = {
                    "success": success,
                    "invalid": invalid_chrt_ids,
                    "errors": errors
                }

        # chrt_id, которых нет ни на одном складе
        all_invalid_chrt_ids = set.intersection(*[res["errors"] for _, res in wh_results.items()])

        return {
            "account": self.account,
            "warehouses": {wh_id: {"success": res["success"], "errors": res["errors"] or None} for wh_id, res in wh_results.items()},
            "invalid_chrt_ids": all_invalid_chrt_ids
        }


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


class StockFBWMarketplaceWB:
    """
    API WB получения отчетов о движении товаров по ФБО.
    """

    BASE_URL = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains"

    def __init__(
        self,
        account_name: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ):
        self.account_name = account_name
        self.api_token = api_token
        self.session = session
        self.headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
        }

    async def _make_wb_request(
        self,
        method: str,
        url: str,
        expected_status: int = status.HTTP_200_OK,
        max_retries: int = 3,
        delay: float = 0.2,
    ) -> dict[str, any]:
        """
        Сделать запрос к WB API.
        """
        for attempt in range(max_retries + 1):
            async with self.session.request(method, url, headers=self.headers) as response:
                if response.status == expected_status:
                    return await response.json()

                error_body = ""

                try:
                    error_body = await response.text()
                except Exception:
                    pass

                if response.status == status.HTTP_429_TOO_MANY_REQUESTS:
                    logger.warning(
                        f"WB API 429 (попытка {attempt + 1}/{max_retries + 1}): "
                        f"url={url}"
                    )

                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Превышено количество попыток ({max_retries + 1}) из-за лимита запросов WB."
                        )

                raise HTTPException(
                    status_code=response.status,
                    detail=f"Ошибка WB API: {response.status} | Body: {error_body[:300]}"
                )

    async def gen_reports_fbw_stocks(self) -> dict[str, str]:
        """
        Сгенерировать отчет по движению товаров по ФБО.
        """
        url = f"{self.BASE_URL}?groupByNm=true&filterPics=0&filterVolume=0"

        result = await self._make_wb_request("GET", url, delay=61.0)

        task_id = result.get("data", {}).get("taskId")

        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка генерации отчета: taskId не получен для аккаунта {self.account_name}"
            )

        return {"account": self.account_name, "task_id": task_id}

    async def check_done_report(
        self,
        task_id: str,
        max_retries: int = 3,
        delay: float = 5.0,
    ) -> bool:
        """
        Проверить готовность отчета о дивежении товаров по ФБО.
        """
        url = f"{self.BASE_URL}/tasks/{task_id}/status"

        for attempt in range(max_retries):
            result = await self._make_wb_request("GET", url, delay=5.0)

            status_value = result.get("data", {}).get("status")

            if status_value == "done":
                return True

            if attempt < max_retries - 1:
                await asyncio.sleep(delay)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Аккаунт {self.account_name}: отчет {task_id} не готов {max_retries} попыток"
        )

    async def get_reports_fbw_stocks_result(
        self,
        task_id: str,
    ) -> dict[str, list[dict[str, any]]]:
        """
        Получить готовый отчет движения товаров по ФБО.
        """
        url = f"{self.BASE_URL}/tasks/{task_id}/download"

        result = await self._make_wb_request("GET", url, delay=61.0)

        return {"account": self.account_name, "data": result}
