import asyncio

from fastapi import APIRouter, Body, HTTPException, status
import aiohttp

from app.config.settings import get_wb_tokens

router  = APIRouter(prefix="/close_cards", tags=["Закрытие карточек"])


# Что принимает? Аккаунт - артикул
# порядок действий
# 1 запросить отчет с группировкой по артикулам
# 2 проверить готовность
# 3 если не готов, подождать и повторить запрос
# 4 если готов, отфильтровать по переданным nm_id
# 5 вернуть ответ с движением товара 

# https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains get запрос на генерацию отчета
# https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/status get проверка отчета
# https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download get получить отчет

@router.post("/preview")
async def close_preview(data: dict[str, list[int]] = Body(..., description="Список артикулов.")):
    async def gen_reports_fbo_stocks(account: str, token: dict, session: aiohttp.ClientSession):
        """Сгенерировать отчет"""

        url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains?groupByNm=true"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        async with session.get(url=url, headers=headers) as response:
                if response.status == status.HTTP_200_OK:
                    result = await response.json()

                    if "data" in result:
                        return {"account": account, "task_id": result["data"].get("taskId")}
                else:
                    raise HTTPException(status_code=response.status, detail="Ошибка при запросе отчета")

    async def check_done_report(account: str, token: dict, task_id: str, session: aiohttp.ClientSession):
        """Проверить готовность отчета"""

        url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/status".format(task_id=task_id)
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        max_retry = 3

        is_done = False

        for _ in range(max_retry):
            async with session.get(url=url, headers=headers) as response:
                if response.status == status.HTTP_200_OK:
                    result = await response.json()

                    if "data" in result:
                        is_done = result["data"].get("status") == "done"
                else:
                    raise HTTPException(status_code=response.status, detail="Ошибка при запросе отчета")

            if is_done:
                break
        
            await asyncio.sleep(5)

        if not is_done:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{account}: task_id - {task_id} | Не получилось проверить результат")

        return {"account": account, "status": is_done}
    
    async def get_reports_fbo_stocks_result(account: str, token: dict, task_id: str, session: aiohttp.ClientSession):
        """Получить готовый отчет"""

        url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download".format(task_id=task_id)
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        async with session.get(url=url, headers=headers) as response:
                if response.status == status.HTTP_200_OK:
                    result = await response.json()

                    return {"account": account, "data": result}
                else:
                    raise HTTPException(status_code=response.status, detail="Ошибка при запросе отчета")

    # получаем токены
    tokens = await get_wb_tokens()
    
    if not tokens:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Нет токенов.")
    
    tasks = []

    # делаем запросы на генерацию отчетов
    async with aiohttp.ClientSession() as session:
        tasks = [gen_reports_fbo_stocks(account=account, token=token, session=session) for account, token in tokens.items() if account.upper() in data]
        results_gen_reports = await asyncio.gather(*tasks)
    
    excs = []

    report_task_ids = {}
    
    for result in results_gen_reports:
        if isinstance(result, Exception):
            excs.append(result)
            
        report_task_ids[result["account"]] = result["task_id"]

    if not report_task_ids:
         raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Не получены id отчетов при генерации.")

    if excs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Ошибки при генерации отчетов: {excs}")

    # проверяем готовность отчетов
    async with aiohttp.ClientSession() as session:
        tasks = [
            check_done_report(
                account=account, 
                token=token, 
                task_id=report_task_ids[account],
                session=session,
            ) for account, token in tokens.items() if account.upper() in data
        ]
        results_check_reports = await asyncio.gather(*tasks)

    excs = []
    done_reports = {}

    for result in results_check_reports:
        if isinstance(result, Exception):
            excs.append(result)
            
        done_reports[result["account"]] = result["status"]
    
    if excs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Ошибки при проверке отчетов: {excs}")
    
    # получаем отчеты
    async with aiohttp.ClientSession() as session:
        tasks = [
            get_reports_fbo_stocks_result(
                account=account, 
                token=token, 
                task_id=report_task_ids[account],
                session=session,
            ) for account, token in tokens.items() if account.upper() in data and done_reports.get(account)
        ]
        results_reports = await asyncio.gather(*tasks)

    excs = []
    reports = {}

    for result in results_reports:
        if isinstance(result, Exception):
            excs.append(result)

        reports[result["account"]] = result["data"]

    if excs:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Ошибки при получении отчетов: {excs}")
    
    if not reports:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Нет отчетов по товарам.")

    # собираем ответ
    result_response = {}

    for account, articles in data.items():
        report_data = reports.get(account.capitalize())

        if not report_data:
            continue

        temp = list(filter(lambda x: x.get("nmId") in articles, report_data))

        result_response[account] = temp
    
    return result_response
