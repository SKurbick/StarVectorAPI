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

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.exception(f"Ошибка обновления остатков: {result}")

    async def _edit_stocks_quantity_for_account(self, account: str, token: str, data):
        """
        Обновить остатки аккаунта на маркетплейсе и в базе данных.
        """
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

        for stock_data in request_stocks:
            article_id = article_ids[account.upper()][stock_data.sku]
            chrt_id = articles_chrt_ids[article_id]
            stocks_list.append(
                {
                    "chrtId": chrt_id,
                    "amount": stock_data.amount
                }
            )

        edit_result = await wb_client.edit_amount_on_warehouses(warehouse_ids, stocks_list)  # возможно пригодится ответ от WB

        logger.info(f"Начало получения остатков для аккаунта: {account}")

        chrt_ids = list(articles_chrt_ids.values())
        logger.debug(f"Аккаунт {account}: запрос остатков для {len(chrt_ids)} chrt_ids на складах {warehouse_ids}")

        get_result = await wb_client.get_amount_from_all_warehouses(warehouse_ids, chrt_ids)

        chrt_id_amount = {}

        for acc, stocks in get_result.items():
            for stock in stocks:
                chrt_id = stock["chrtId"]
                amount = stock["amount"]

                chrt_id_amount[chrt_id] = amount

        last_datetime = datetime.datetime.today()
        data_to_update = []

        for sku in all_skus:
            article_id = article_ids[account.upper()].get(sku)
            chrt_id = articles_chrt_ids.get(article_id)
            amount = chrt_id_amount.get(chrt_id)

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
