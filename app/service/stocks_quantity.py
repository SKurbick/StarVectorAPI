import asyncio
import datetime

from app.config.settings import get_wb_tokens
from app.domain.models import StocksQuantity, UpdateStocksQuantityResponseModel
from app.infrastructure.WildberriesAPI.marketplace import WarehouseMarketplaceWB, LeftoversMarketplace
from app.repository import StocksQuantityRepository


class StocksQuantityService:
    def __init__(self, stocks_quantity_repository: StocksQuantityRepository):
        self.stocks_quantity_repository = stocks_quantity_repository

    async def get_all_data(self) -> list[StocksQuantity]:
        return await self.stocks_quantity_repository.get_all_data()

    async def edit_stocks_quantity(self, edit_data: dict[str, UpdateStocksQuantityResponseModel]):
        """
        Обновить остатки по аккаунтам на маркетплейсе и в базе данных.
        """
        api_tokens = await get_wb_tokens()
        tasks = []

        for account, account_data in edit_data.items():
            token = api_tokens[account.capitalize()]
            warehouse_client = WarehouseMarketplaceWB(token=token)
            warehouses = await warehouse_client.get_account_warehouse()
            warehouse_ids = [w["id"] for w in warehouses]

            if not warehouse_ids:
                continue

            wb_client = LeftoversMarketplace(token=token, account=account)
            stocks_list = account_data.model_dump()["stocks"]

            task = asyncio.create_task(
                wb_client.edit_amount_on_warehouses(warehouse_ids, stocks_list)
            )
            tasks.append(task)

        update_stockgathers_result = await asyncio.gather(*tasks, return_exceptions=True)  # возможно пригодится ответ от WB

        tasks = []
        account_warehouse_map = {}

        for account, account_data in edit_data.items():
            token = api_tokens[account.capitalize()]
            warehouse_client = WarehouseMarketplaceWB(token=token)
            warehouses = await warehouse_client.get_account_warehouse()
            warehouse_ids = [w["id"] for w in warehouses]
            account_warehouse_map[account] = warehouse_ids

            if not warehouse_ids:
                continue

            wb_client = LeftoversMarketplace(token=token, account=account)
            barcodes = [item.sku for item in account_data.stocks]

            task = asyncio.create_task(
                wb_client.get_amount_from_all_warehouses(warehouse_ids, barcodes)
            )
            tasks.append(task)

        get_amount_gather_result = await asyncio.gather(*tasks, return_exceptions=True)  

        data_to_update = []
        last_datetime = datetime.datetime.today()

        for result in get_amount_gather_result:
            if isinstance(result, Exception):
                print(str(result))
                continue

            print(result)
            for account, stocks in result.items():
                for stock in stocks:
                    data_to_update.append(
                        (
                            account,
                            str(stock["sku"]),
                            "ФБС", # или можно брать из warehouse info
                            stock["amount"],
                            last_datetime
                        )
                    )

        print(data_to_update)
        if data_to_update:
            await self.stocks_quantity_repository.update_fbs_data(data_to_update)
