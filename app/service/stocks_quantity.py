import asyncio
import datetime
import logging

from app.config.settings import get_wb_tokens
from app.domain.models import StocksQuantity, UpdateStocksQuantityResponseModel
from app.infrastructure.WildberriesAPI.marketplace import WarehouseMarketplaceWB, LeftoversMarketplace
from app.repository import StocksQuantityRepository
from app.service.card_data import CardDataService

logger = logging.getLogger(__name__)


class StocksQuantityService:
    def __init__(
        self,
        stocks_quantity_repository: StocksQuantityRepository,
        card_data_service: CardDataService,
    ):
        self.stocks_quantity_repository = stocks_quantity_repository
        self.card_data_service = card_data_service

    async def get_all_data(self) -> list[StocksQuantity]:
        return await self.stocks_quantity_repository.get_all_data()

    async def edit_stocks_quantity(self, edit_data: dict[str, UpdateStocksQuantityResponseModel]):
        """
        Обновить остатки по аккаунтам на маркетплейсе и в базе данных.
        """
        api_tokens = await get_wb_tokens()
        tasks = []

        for account, account_data in edit_data.items():
            tasks.append(asyncio.create_task(self._edit_stocks_quantity_for_account(
                account=account,
                token=api_tokens[account.capitalize()],
                data=account_data
            )))

        finally_result = {
            "accounts": {},
            "errors": []
        }

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    error_message = f"Ошибка обновления остатков: {result}"
                    logger.exception(error_message)
                    finally_result["errors"].append(error_message)
                    continue

                finally_result["accounts"].update(result)

        return finally_result

    async def _edit_stocks_quantity_for_account(self, account: str, token: str, data):
        """
        Обновить остатки аккаунта на маркетплейсе и в базе данных.
        """
        # получаем склады продавца для аккаунта
        warehouse_client = WarehouseMarketplaceWB(token=token)
        warehouses = await warehouse_client.get_account_warehouse()
        warehouse_ids = [w["id"] for w in warehouses]

        if not warehouse_ids:
            return

        wb_client = LeftoversMarketplace(token=token, account=account)

        request_stocks = data.stocks
        all_skus = [item.sku for item in request_stocks]
        article_ids = await self.card_data_service.get_article_ids_by_barcodes(
            {account: all_skus}
        )
        articles_chrt_ids = await self.card_data_service.get_chrt_ids_by_article_ids(
            list(article_ids[account.upper()].values())
        )

        stocks_list = []
        barcodes_without_chrt_id = set()

        # формируем данные для запроса
        for stock_data in request_stocks:
            article_id = article_ids[account.upper()][stock_data.sku]
            chrt_id = articles_chrt_ids[article_id]

            if not chrt_id:
                barcodes_without_chrt_id.add(stock_data.sku)
                continue

            stocks_list.append(
                {
                    "chrtId": chrt_id,
                    "amount": stock_data.amount
                }
            )

        edit_result = {}

        # отправляем запрос на редактирование
        if stocks_list:
            edit_result = await wb_client.edit_amount_on_warehouses(warehouse_ids, stocks_list)  # возможно пригодится ответ от WB
            await asyncio.sleep(2)  # чтобы остатки успели обновиться на wb

        invalid_chrt_ids = edit_result.get("invalid_chrt_ids", set())
        whs_info = edit_result.get("warehouses", [])

        logger.info(f"Начало получения остатков для аккаунта: {account}")

        # получаем новые остатки с вб
        chrt_ids = list(articles_chrt_ids.values())
        logger.debug(f"Аккаунт {account}: запрос остатков для {len(chrt_ids)} chrt_ids на складах {warehouse_ids}")
        get_result = await wb_client.get_amount_from_all_warehouses(warehouse_ids, chrt_ids)

        chrt_id_amount = {}

        for acc, stocks in get_result.items():
            for stock in stocks:
                chrt_id = stock["chrtId"]
                amount = stock["amount"]

                chrt_id_amount[chrt_id] = amount

        # формируем данные для обновления в бд
        last_datetime = datetime.datetime.today()
        data_to_update = []
        invalid_barcodes = []

        for sku in all_skus:
            article_id = article_ids[account.upper()].get(sku)
            chrt_id = articles_chrt_ids.get(article_id)
            amount = chrt_id_amount.get(chrt_id)

            if chrt_id in invalid_chrt_ids:
                invalid_barcodes.append(sku)

            if amount is not None:
                data_to_update.append(
                    (
                        acc,
                        sku,
                        "ФБС", # или можно брать из warehouse info
                        amount,
                        last_datetime
                    )
                )

        if data_to_update:
            logger.info(f"Обновление БД: {len(data_to_update)} записей")
            await self.stocks_quantity_repository.update_fbs_data(data_to_update)
            logger.info("Обновление остатков в БД успешно завершено")
        else:
            logger.warning("Нет данных для обновления в БД")

        return {
            account: {
                "warehouses": whs_info,
                "barcodes_with_invalid_chrt_id": invalid_barcodes or None,
                "barcodes_without_chrt_id": list(barcodes_without_chrt_id) or None
            }
        }
