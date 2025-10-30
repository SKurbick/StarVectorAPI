import asyncio
import logging

import aiohttp

from app.infrastructure.WildberriesAPI.marketplace import (
    CardMarketplaceWB, WarehouseMarketplaceWB, LeftoversMarketplace
)


logger = logging.getLogger(__name__)


class VirtaulBalance:
    """Изменяет виртуальные остатки товаров на всех складах WB."""

    def __init__(self, account_name: str, api_token: str):
        self.account_name = account_name
        self.api_token = api_token

    async def update_virtual_balance(self, nm_ids: list[int], new_amount: int) -> dict[str, dict]:
        """
        Для переданных nm_ids:
        - получает баркоды
        - получает склады аккаунта
        - отправляет новые остатки
        - проверяет результат
        """
        async with aiohttp.ClientSession() as session:
            card_fetcher = CardMarketplaceWB(self.account_name, self.api_token, session)
            nm_to_barcodes = await card_fetcher.get_barcodes_by_nmid(nm_ids)

            all_barcodes = [b for lst in nm_to_barcodes.values() for b in lst]

            if not all_barcodes:
                logger.warning(f"[{self.account_name}] Нет баркодов по nm_ids: {nm_ids}")
                return {}

            warehouses_api = WarehouseMarketplaceWB(self.api_token)
            warehouses_data = await warehouses_api.get_account_warehouse()

            if not warehouses_data:
                logger.error(f"[{self.account_name}] Не удалось получить список складов.")
                return {}

            leftovers_api = LeftoversMarketplace(self.api_token, self.account_name)

            result = {}
            edit_payload = [
                    {"sku": b, "amount": new_amount}
                    for b in all_barcodes
                ]

            for warehouse in warehouses_data:
                wh_name = warehouse.get("name")
                wh_id = warehouse.get("id")

                if not wh_id:
                    logger.warning(f"[{self.account_name}] Пропущен склад без ID: {warehouse}")
                    continue

                max_attempts = 3
                attempts = 1

                while attempts <= max_attempts:
                    logger.info(f"[{self.account_name}] Обновление остатков склада '{wh_name}' ({wh_id}). Попытка {attempts}/{max_attempts}")
                    status = await leftovers_api.edit_amount_from_warehouses(wh_id, edit_payload)

                    if status is not None:
                        if status == 429:
                            logger.warning(f"[429] {self.account_name} — лимит. Ждём 65 сек...")
                            await asyncio.sleep(65)
                            attempts += 1
                            continue
                        else:
                            logger.error(f"[{self.account_name}] Ошибка при обновлении остатков. wh_id: {wh_id}. Статус: {status}")
                            break
                    
                    logger.info(f"[{self.account_name}] Обновление остатков склада '{wh_name}' ({wh_id}) выполнено.")

                stocks_data = await leftovers_api.get_amount_from_warehouses(wh_id, all_barcodes)
                updated_barcodes = [
                    s["sku"] for s in stocks_data.get(self.account_name, [])
                    if s.get("amount") == self.new_amount
                ]

                result[wh_name] = {
                    "updated": updated_barcodes,
                    "invalid": [
                        barcode for barcode in all_barcodes if barcode not in all_barcodes
                    ]
                }

            return result
