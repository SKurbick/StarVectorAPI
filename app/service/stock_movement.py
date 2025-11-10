import aiohttp
import asyncio
from fastapi import HTTPException, status
import logging

from app.config.settings import get_wb_tokens
from app.infrastructure.WildberriesAPI.marketplace import StockFBWMarketplaceWB


logger = logging.getLogger(__name__)


class StockMovementService:
    async def get_stock_movement(self, data: dict[str, list[int]]) -> dict[str, list[dict[str, any]]]:
        """
        Получить отчет о движении товаров по ФБО по аккаунтам.
        """
        tokens = await get_wb_tokens()

        if not tokens:
            logger.error("Отсутствую токены аккаунтов WB.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Отсутствую токены аккаунтов WB."
            )

        requested_accounts_upper = {acc.upper() for acc in data.keys()}
        valid_accounts = {
            acc: token for acc, token in tokens.items()
            if acc.upper() in requested_accounts_upper
        }

        if not valid_accounts:
            logger.error(f"Не найдено соответствующих учетных записей: {requested_accounts_upper}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Не найдено соответствующих учетных записей для предоставленных данных."
            )
        
        logger.info(f"Получение отчетов по движению товаров для аккаунтов: {valid_accounts.keys()}")

        async with aiohttp.ClientSession() as session:
            # генерация отчетов
            gen_tasks = []
            clients = {}

            for account, token in valid_accounts.items():
                client = StockFBWMarketplaceWB(
                    account_name=account,
                    api_token=token,
                    session=session
                )
                clients[account] = client
                gen_tasks.append(client.gen_reports_fbw_stocks())

            gen_results = await asyncio.gather(*gen_tasks, return_exceptions=True)

            task_map = {}
            errors = []

            for res in gen_results:
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    task_map[res["account"]] = res["task_id"]

            if errors:
                logger.error(f"Ошибки при формировании отчета: {errors}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ошибки при формировании отчета: {errors}"
                )

            # Проверка готовности
            check_tasks = [
                clients[account].check_done_report(task_id)
                for account, task_id in task_map.items()
            ]
            await asyncio.gather(*check_tasks, return_exceptions=False)

            # Загрузка отчётов
            download_tasks = [
                clients[account].get_reports_fbw_stocks_result(task_id)
                for account, task_id in task_map.items()
            ]
            download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

            reports = {}
            errors.clear()

            for res in download_results:
                if isinstance(res, Exception):
                    errors.append(res)
                else:
                    reports[res["account"]] = res["data"]

            if errors:
                logger.error(f"Ошибки при загрузке отчетов: {errors}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ошибки при загрузке отчетов: {errors}"
                )

        result_response = {}

        for account, nm_ids in data.items():
            normalized_acc = account.capitalize()
            report = reports.get(normalized_acc)

            if not report:
                result_response[account] = {
                    "data": [],
                    "not_found": nm_ids.copy()
                }
                continue

            report_nm_ids = {item.get("nmId") for item in report if item.get("nmId") is not None}
            found_items = []
            not_found_items = []

            for nm_id in nm_ids:
                if nm_id in report_nm_ids:
                    item = next((x for x in report if x.get("nmId") == nm_id), None)

                    if item:
                        found_items.append({
                            "nm_id": item["nmId"],
                            "warehouses": item.get("warehouses", []),
                        })
                else:
                    not_found_items.append(nm_id)

            result_response[account] = {
                "data": found_items,
                "not_found": not_found_items
            }

        return result_response
