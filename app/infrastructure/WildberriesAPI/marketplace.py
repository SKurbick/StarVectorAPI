import asyncio
import time

import aiohttp


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


