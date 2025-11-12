import aiohttp
import asyncio
from fastapi import HTTPException, status
import logging

from app.config.settings import get_wb_tokens
from app.infrastructure.WildberriesAPI.marketplace import StockFBWMarketplaceWB
from app.infrastructure.cache import redis_cache_async


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

        logger.info(f"Получение отчетов по движению товаров для аккаунтов: {list(valid_accounts.keys())}")

        async with aiohttp.ClientSession() as session:
            tasks = [self.get_stock_movement_by_account(acc, token, session) for acc, token in valid_accounts.items()]
            report_results = await asyncio.gather(*tasks, return_exceptions=True)

        reports = {}
        errors = []

        for res in report_results:
            if isinstance(res, Exception):
                errors.append(res)
            else:
                reports[res["account"]] = res.get("data", [])

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
                "not_found": not_found_items,
            }

        return {"result": result_response, "errors": errors, "success": not errors}

    @redis_cache_async(ttl=65, exclude_args={"token", "session"})
    async def get_stock_movement_by_account(self, account: str, token: str, session: aiohttp.ClientSession):
        api_client = StockFBWMarketplaceWB(
            account_name=account,
            api_token=token,
            session=session,
        )

        try:
            gen_report_result = await api_client.gen_reports_fbw_stocks()
        except Exception as e:
            logger.error(f"Ошибка при формировании отчета [{account}]: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ошибка при формировании отчета [{account}]: {e}"
            )

        task_id = gen_report_result["task_id"]

        try:
            report_is_done = await api_client.check_done_report(task_id)
        except Exception as e:
            logger.error(f"Ошибка при проверке готовности отчета [{account}]: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ошибка при проверке готовности отчета [{account}]: {e}"
            )

        if not report_is_done:
            return {"account": account, "data": None}

        try:
            return await api_client.get_reports_fbw_stocks_result(task_id)
        except Exception as e:
            logger.error(f"Ошибка при получении отчета [{account}]: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ошибка при получении отчета [{account}]: {e}"
            )
