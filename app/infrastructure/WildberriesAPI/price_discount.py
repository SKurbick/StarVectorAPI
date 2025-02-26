import asyncio
import json
import time
from pprint import pprint
from typing import List

import aiohttp
from aiohttp import ClientSession


class PricesAndDiscounts:
    """API Цены и товары"""
    pass


class ListOfGoodsPricesAndDiscounts:
    """API Список товаров"""

    def __init__(self, token):
        self.token = token
        self.base_url = "https://discounts-prices-api.wildberries.ru"
        self.url = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/{}"
        self.post_url = "https://discounts-prices-api.wildberries.ru/api/v2/upload/task"

        self.headers = {
            "Authorization": self.token,
            'Content-Type': 'application/json'
        }

    async def details_upload_task(self, task_id, limit=1000) -> List[dict]:
        result = []
        url = self.base_url + "/api/v2/history/goods/task"
        offset = 0
        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "uploadID": task_id
            }
            for i in range(10):
                try:
                    async with ClientSession() as session:
                        async with session.get(url, headers=self.headers, params=params) as response:
                            response_result = await response.json()
                            print(f"[func] details_upload_task status - {response.status}")
                            if "data" in response_result:
                                if response_result['data'] is not None:
                                    result.extend(response_result['data']['historyGoods'])
                                    break
                                else:
                                    break
                            elif len(response_result) == 0:
                                break
                            elif response.status == 429:
                                print("попытка:", i, "sleep 10 sec")
                                await asyncio.sleep(10)
                                continue
                            else:
                                break
                except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
                    print(e, "sleep 36 sec")
                    await asyncio.sleep(36)
            if i == 9 or "data" not in response_result or response_result['data'] is None or \
                    response_result["data"]["listGoods"] is None or len(response_result["data"]["listGoods"]) == 0:
                print("прерывание бесконечного цикла")
                # для того что бы прервать бесконечный цикл
                break
            else:  # пагинация
                offset += limit
            return result

    async def get_log_for_nm_ids(self, filter_nm_ids, account=None) -> dict:
        """Получение цен и скидок по совпадению с nmID"""
        url = self.url.format("filter")
        nm_ids = [*filter_nm_ids]
        nm_ids_list = {}
        offset = 0
        limit = 1000
        while True:
            params = {
                "limit": limit,
                "offset": offset,
            }

            for i in range(1, 10):
                try:
                    async with ClientSession() as session:
                        async with session.get(url, headers=self.headers, params=params) as response:
                            response_result = await response.json()
                            print(f"[func] get_log_for_nm_ids status - {response.status}")
                            if "data" in response_result:
                                if response_result['data'] is not None:
                                    for card in response_result["data"]["listGoods"]:
                                        if card["nmID"] in nm_ids:
                                            nm_ids_list[card["nmID"]] = {
                                                "price": card["sizes"][0]["price"],
                                                "discount": card["discount"]
                                            }
                                            nm_ids.remove(card["nmID"])
                                    break
                                else:
                                    break
                            elif len(response_result) == 0:
                                break
                            elif response.status == 429:
                                print(nm_ids)
                                print("попытка:", i, "sleep 10 sec")
                                await asyncio.sleep(10)
                                continue
                            else:
                                break
                except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
                    print(e, "sleep 36 sec")
                    await asyncio.sleep(36)

            print("Дошел до условия прерывания бесконечного цикла")
            print("offset", offset)
            if len(nm_ids) == 0 or i == 9 or "data" not in response_result or response_result['data'] is None or \
                    response_result["data"]["listGoods"] is None or len(response_result["data"]["listGoods"]) == 0:
                print("прерывание бесконечного цикла")
                # для того что бы прервать бесконечный цикл
                break
            else:  # пагинация
                offset += limit
        if len(nm_ids) != 0:
            print(f"в запросе просмотра цен есть невалидные артикулы -> {account}:", nm_ids)
        return nm_ids_list

    async def get_all_log_for_nm_ids(self) -> dict:
        # в методе не продуманна пагинация
        """Получение цен и скидок со всех валидных артикулов"""
        url = self.url.format("filter")
        nm_ids_list = {}
        print("В функции get_log_for_nm_ids")
        offset = 0
        limit = 1000
        while True:
            params = {
                "limit": limit,
                "offset": offset,
            }

            for i in range(1, 10):
                try:
                    async with ClientSession() as session:
                        async with session.get(url, headers=self.headers, params=params) as response:
                            response_result = await response.json()
                            if "data" in response_result:
                                if response_result['data'] is not None:
                                    for card in response_result["data"]["listGoods"]:
                                        nm_ids_list[card["nmID"]] = {
                                            "price": card["sizes"][0]["price"],
                                            "discount": card["discount"]
                                        }
                                    break
                                else:
                                    break
                            elif len(response_result) == 0:
                                break
                            elif response.status == 429:
                                print("попытка:", i, "sleep 10 sec")
                                await asyncio.sleep(10)
                                continue
                            else:
                                break
                except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
                    print(e, "sleep 36 sec")
                    await asyncio.sleep(36)

            print("Дошел до условия прерывания бесконечного цикла")
            print("offset", offset)
            if i == 9 or "data" not in response_result or response_result['data'] is None or \
                    response_result["data"]["listGoods"] is None or len(response_result["data"]["listGoods"]) == 0:
                print("прерывание бесконечного цикла")
                # для того что бы прервать бесконечный цикл
                break
            else:  # пагинация
                offset += limit
        return nm_ids_list

    async def add_new_price_and_discount(self, account: str, data: list, step=1000):
        url = self.post_url
        for start in range(0, len(data), step):
            butch_data = data[start: start + step]
            for _ in range(10):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url=url, headers=self.headers, json={"data": butch_data}) as response:
                            response_result = await response.json()
                            # todo логирование
                            print("Артикулы на изменение цены:", butch_data)
                            print("price and discount edit result:", response_result)
                            if (response.status in (200, 208) or response_result['errorText'] in
                                    ("Task already exists", "No goods for process")):
                                break
                            if response.status == 429:
                                print('429 error add_new_price_and_discount sleep 23')
                                await asyncio.sleep(23)
                except (Exception, aiohttp.ClientError, aiohttp.HTTPError) as e:
                    print(f'ERROR {e} add_new_price_and_discount')
                    await asyncio.sleep(36)
        return {account: response_result}
