import asyncio
import logging

import aiohttp


logger = logging.getLogger(__name__)


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
