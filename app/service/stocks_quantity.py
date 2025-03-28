import asyncio
import datetime
from pprint import pprint
from typing import List, Dict

from app.config.settings import get_wb_tokens
from app.repository import StocksQuantityRepository
from app.domain.models import StocksQuantity, UpdateStocksQuantityResponseModel
from app.infrastructure.WildberriesAPI.marketplace import WarehouseMarketplaceWB, LeftoversMarketplace


class StocksQuantityService:
    def __init__(self, stocks_quantity_repository: StocksQuantityRepository):
        self.stocks_quantity_repository = stocks_quantity_repository

    async def get_all_data(self) -> List[StocksQuantity]:
        return await self.stocks_quantity_repository.get_all_data()

    #
    async def edit_stocks_quantity(self, edit_data: Dict[str, UpdateStocksQuantityResponseModel]):
        api_tokens = await get_wb_tokens()  # получение всех токенов
        tasks = []
        actualize_data = {}

        for account, account_data in edit_data.items():
            skus = [stocks_data.sku for stocks_data in account_data.stocks]
            actualize_data[account] = skus
            token = api_tokens[account.capitalize()]
            warehouses = await WarehouseMarketplaceWB(token=token).get_account_warehouse()
            qty_edit = LeftoversMarketplace(token=token, account=account)
            print(account_data.model_dump())
            task = asyncio.create_task(qty_edit.edit_amount_from_warehouses(warehouse_id=warehouses[0]["id"],
                                                                            edit_barcodes_list=account_data.model_dump()['stocks']))

            print("actualize_data",actualize_data)

            tasks.append(task)

        gather_result = await asyncio.gather(*tasks)  # возможно пригодится ответ от WB

        tasks = []
        for account, account_data in actualize_data.items():
            token = api_tokens[account.capitalize()]
            qty_state = LeftoversMarketplace(token, account=account)
            warehouses = await WarehouseMarketplaceWB(token=token).get_account_warehouse()
            task = asyncio.create_task(qty_state.get_amount_from_warehouses(warehouse_id=warehouses[0]['id'], barcodes=account_data))
            tasks.append(task)
        gather_result = await asyncio.gather(*tasks)  # получение новых остатков
        data_to_update = []
        last_datetime = datetime.datetime.today()
        for gr in gather_result:
            for account, account_data in gr.items():
                for quantity_data in account_data:
                    data_to_update.append(
                        (account, str(quantity_data['sku']), "ФБС", quantity_data['amount'], last_datetime)
                    )
        # обновление остатков в БД
        await self.stocks_quantity_repository.update_fbs_data(data_to_update)
