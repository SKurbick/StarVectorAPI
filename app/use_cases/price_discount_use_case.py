import asyncio
'''Модуль пока не участвует в разработке'''

from app.config.settings import get_wb_tokens
from app.domain.models import PriceDiscountResponseModel
from app.infrastructure.WildberriesAPI.price_discount import ListOfGoodsPricesAndDiscounts


class PriceDiscountUseCase:
    def __init__(self, price_discount_api: ListOfGoodsPricesAndDiscounts):
        self.price_discount_api = price_discount_api

    async def update_data(self, data: PriceDiscountResponseModel):
        update_result = []
        try:
            api_tokens = await get_wb_tokens()
            tasks = []
            for account, token in api_tokens.items():
                list_of_goods_wb = ListOfGoodsPricesAndDiscounts(token=token)
                account_update_data = data.model_dump(exclude_none=True)['update_data'][account.capitalize()]
                task = asyncio.create_task(list_of_goods_wb.add_new_price_and_discount(account=account, data=account_update_data))
                tasks.append(task)
            together_result = await asyncio.gather(*tasks, return_exceptions=True)

            upload_data_tasks = []
            for res in together_result:
                for account, r_data in res.items():
                    upload_task_id = r_data["data"]["id"]
                    token = api_tokens[account.capitalize()]
                    list_of_goods_wb = ListOfGoodsPricesAndDiscounts(token=token)
                    task = asyncio.create_task(list_of_goods_wb.details_upload_task(task_id=upload_task_id))
                    upload_data_tasks.append(task)

            upload_data_together_result = await asyncio.gather(*upload_data_tasks)

            for upload_res in upload_data_together_result:
                update_result.extend(upload_res)

            # todo валидировать выходные параметры по запросу с АПИ ВБ
            # todo обновление новых данных в бд

            return {"status": 200, "message": "успешно ебать 👍 поздравляю "}
        except Exception as e:
            return {"status": 401, "message": f"error: {e}"}
