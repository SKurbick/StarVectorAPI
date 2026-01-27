import asyncio
import datetime
import logging

from app.config.settings import get_wb_tokens
from app.domain.models import StocksQuantity, UpdateStocksQuantityResponseModel, StocksFBSQuantityInDB
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

    async def get_current_stocks_for_account(self, account: str, skus: list[str]) -> dict[str, dict[str, any]]:
        """Получить актуальные остатки аккаунта с маркетплейса."""
        api_tokens = await get_wb_tokens()
        token = api_tokens.get(account.capitalize())

        if not token:
            raise ValueError(f"Не найден токен аккаунта: {account}")

        warehouse_client = WarehouseMarketplaceWB(token=token)
        warehouses = await warehouse_client.get_account_warehouse()
        warehouse_ids = [w["id"] for w in warehouses]

        if not warehouse_ids:
            return

        article_ids = await self.card_data_service.get_article_ids_by_barcodes(
            {account: skus}
        )
        articles_chrt_ids = await self.card_data_service.get_chrt_ids_by_article_ids(
            list(article_ids[account.upper()].values())
        )

        barcodes_without_chrt_id = set()

        all_chrt_ids = []
        # формируем данные для запроса
        for sku in skus:
            article_id = article_ids[account.upper()][sku]
            chrt_id = articles_chrt_ids[article_id]

            if not chrt_id:
                barcodes_without_chrt_id.add(sku)
                continue

            all_chrt_ids.append(chrt_id)

        wb_client = LeftoversMarketplace(token=token, account=account)
        stocks_result = await wb_client.get_amount_from_all_warehouses(
            warehouse_ids=warehouse_ids,
            chrt_ids=all_chrt_ids
        )

        chrt_id_amount = {}

        for _, stocks in stocks_result.items():
            for stock in stocks:
                chrt_id = stock["chrtId"]
                amount = stock["amount"]
                chrt_id_amount[chrt_id] = amount
        
        sku_amount = {}

        for sku in skus:
            if sku in barcodes_without_chrt_id:
                continue

            article_id = article_ids[account.upper()].get(sku)
            chrt_id = articles_chrt_ids.get(article_id)
            amount = chrt_id_amount.get(chrt_id)

            if amount is not None:
                sku_amount[sku] = amount
        
        return {
            account.capitalize(): {
                "stocks": sku_amount,
                "barcodes_without_chrt_id": list(barcodes_without_chrt_id) or None
            }
        }

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

    async def update_stocks_in_db(self, data: list[StocksFBSQuantityInDB]):
        """Обновить виртуальные остатки в базе данных."""
        data_to_update = []
        last_datetime = datetime.datetime.today()

        for item in data:
            data_to_update.append(
                        (
                            item.article_id,
                            item.barcode,
                            "ФБС",
                            item.quantity,
                            last_datetime
                        )
                    )

        if data_to_update:
            logger.info(f"Обновление БД: {len(data_to_update)} записей")
            await self.stocks_quantity_repository.update_fbs_data(data_to_update)
            logger.info("Обновление остатков в БД успешно завершено")
        else:
            logger.warning("Нет данных для обновления в БД")

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
            article_id = article_ids[account.upper()].get(stock_data.sku)
            chrt_id = articles_chrt_ids.get(article_id)

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
            await asyncio.sleep(3)

        invalid_chrt_ids = edit_result.get("invalid_chrt_ids", set())
        whs_info = edit_result.get("warehouses", [])

        # получаем новые остатки с вб
        logger.info(f"Начало получения остатков для аккаунта: {account}")
        get_stocks_result = await self.get_current_stocks_for_account(account, all_skus)
        sku_amount = get_stocks_result[account.capitalize()]["stocks"]

        # формируем данные для обновления в бд
        data_to_update: list[StocksFBSQuantityInDB] = []
        invalid_barcodes = []

        for sku in all_skus:
            article_id = article_ids[account.upper()].get(sku)
            chrt_id = articles_chrt_ids.get(article_id)
            amount = sku_amount.get(sku)

            if chrt_id in invalid_chrt_ids:
                invalid_barcodes.append(sku)
                continue

            if amount is not None:
                data_to_update.append(
                    StocksFBSQuantityInDB(
                        article_id=article_id,
                        barcode=sku,
                        quantity=amount
                    )
                )

        await self.update_stocks_in_db(data_to_update)

        return {
            account: {
                "warehouses": whs_info,
                "barcodes_with_invalid_chrt_id": invalid_barcodes or None,
                "barcodes_without_chrt_id": list(barcodes_without_chrt_id) or None
            }
        }
