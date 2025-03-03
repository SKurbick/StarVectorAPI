import asyncio
from pprint import pprint
from typing import List, Dict

from app.config.settings import get_wb_tokens
from app.domain.models import PriceDiscountResponseModel, PriceDiscountDB, ResponseMessage

from app.repository.price_discount import PriceDiscountRepository
from app.infrastructure.WildberriesAPI.price_discount import ListOfGoodsPricesAndDiscounts


class PriceDiscountService:
    def __init__(
            self,
            price_discount_repository: PriceDiscountRepository,
    ):
        self.price_discount_repository = price_discount_repository

    async def update(self, data: PriceDiscountResponseModel):
        update_result = []
        print(data)

        api_tokens = await get_wb_tokens()  # получение всех токенов
        tasks = []
        for account in data.update_data:
            token = api_tokens[account.capitalize()]  # токен по аккаунту из post запроса
            list_of_goods_wb = ListOfGoodsPricesAndDiscounts(token=token)
            account_update_data = data.update_data[account].model_dump(exclude_none=True)['data']
            pprint(account_update_data)
            task = asyncio.create_task(list_of_goods_wb.add_new_price_and_discount(data=account_update_data, account=account))
            tasks.append(task)
        together_result = await asyncio.gather(*tasks, return_exceptions=True)

        upload_data_tasks = []
        await asyncio.sleep(3)

        for res in together_result:
            for account, r_data in res.items():
                print(account, r_data)
                upload_task_id = r_data["data"]["id"]
                print(upload_task_id)
                token = api_tokens[account.capitalize()]
                list_of_goods_wb = ListOfGoodsPricesAndDiscounts(token=token)
                task = asyncio.create_task(list_of_goods_wb.details_upload_task(task_id=upload_task_id))
                upload_data_tasks.append(task)

        upload_data_together_result = await asyncio.gather(*upload_data_tasks)

        for upload_res in upload_data_together_result:
            update_result.extend([PriceDiscountDB(**up_res) for up_res in upload_res])

        # todo валидировать выходные параметры по запросу с АПИ ВБ
        # обновление новых данных в бд
        print(update_result)
        await self.price_discount_repository.update_price_and_discount_data(update_data=update_result)
