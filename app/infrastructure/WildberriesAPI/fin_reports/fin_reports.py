import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import AsyncGenerator

import aiohttp


class WBFinReportFetcher:
    BASE_URL = "https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod"

    def __init__(
        self,
        account: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ):
        self.account = account
        self.api_token = api_token
        self.session = session

        self.next_request_time = datetime.min

    async def _wait_if_needed(self):
        """Ждём, если для аккаунта ещё не прошёл интервал между запросами."""
        last_call = self.next_request_time
        now = datetime.now()

        if now < last_call:
            wait = (last_call - now).total_seconds()

            logging.warning(f"[{self.account}] Ждём {wait:.1f} сек до следующего запроса")
            await asyncio.sleep(wait)

    async def _make_request(self, params: dict) -> dict:
        """Выполняет один запрос с обработкой ошибок."""
        headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json"
        }

        async with self.session.get(self.BASE_URL, headers=headers, params=params) as response:
            if response.status == 429:
                logging.warning(f"[429] {self.account} | Лимит. Ждём 65 сек...")

                self.next_request_time = datetime.now() + timedelta(seconds=65)

                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=429,
                    message="Too Many Requests"
                )

            if response.status == 400:
                text = await response.text()
                logging.warning(f"[400] {self.account} | Bad Request: {text[:500]}")

                # Критические ошибки — не повторяем
                if any(w in text.lower() for w in ["invalid", "token", "rrdid", "malformed"]):
                    raise ValueError(f"Критическая ошибка 400: {text[:200]}")
                else:
                    # Временная ошибка — можно повторить
                    self.next_request_time = datetime.now() + timedelta(seconds=65)

                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=400,
                        message="Bad Request (retryable)"
                    )

            if response.status != 200:
                text = await response.text()

                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=text[:500]
                )

            raw = await response.text()

            if not raw.strip():
                return []

            try:
                data = json.loads(raw)

                return data if isinstance(data, list) else []
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error: {e}")
                logging.error(f"Raw: {raw[:1000]}")
                return []

    async def fetch(self, date_from: str, date_to: str, limit: int = 50000) -> AsyncGenerator[list[dict], None]:
        """
        Получает ежедневный финансовый отчёт за указанную дату (в формате 'YYYY-MM-DD').
        Возвращает список записей (словарей).
        """
        logging.info(f"{self.account} | Запрос за {date_from} - {date_to}")

        next_rrdid = 0
        all_records_count = 0
        attempt = 0
        max_attempts = 20

        # Параметры для ежедневного отчёта
        base_params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "period": "daily",
            "limit": limit,
        }

        while attempt < max_attempts:
            await self._wait_if_needed()

            params = {**base_params, "rrdid": next_rrdid}

            try:
                data = await self._make_request(params)

                if not data:
                    break

                next_rrdid = data[-1]["rrd_id"]
                delay = 70 if len(data) >= 25000 else 60
                self.next_request_time = datetime.now() + timedelta(seconds=delay)
                attempt = 0  # сброс счётчика при успехе

                logging.info(f"{self.account} | +{len(data)} строк за {date_from} - {date_to}")

                records_count = len(data)
                all_records_count += records_count

                yield data

                if records_count < limit:
                    break

            except aiohttp.ClientPayloadError as e:
                logging.warning(f"[Payload] {self.account}: {e}. Попытка {attempt + 1}")
                attempt += 1
                await asyncio.sleep(5 * attempt)
                continue

            except (aiohttp.ClientResponseError, ValueError) as e:
                if isinstance(e, ValueError):
                    logging.error(f"Критическая ошибка: {e}")
                    break
                if e.status == 429 or "retryable" in str(e):
                    attempt += 1
                    await asyncio.sleep(2 * attempt)
                    continue
                else:
                    logging.error(f"Необработанная ошибка: {e}")
                    break

            except asyncio.TimeoutError:
                logging.warning(f"Timeout {self.account}, попытка {attempt + 1}")
                attempt += 1

                await asyncio.sleep(5 * attempt)
                continue

            except (aiohttp.ClientConnectorError, ConnectionResetError) as e:
                logging.warning(f"Сеть {self.account}: {e}, попытка {attempt + 1}")
                attempt += 1

                await asyncio.sleep(5 * attempt)
                continue

            except Exception as e:
                logging.error(f"Неизвестная ошибка {self.account}: {e}", exc_info=True)
                break

        if attempt >= max_attempts:
            logging.warning(f"{self.account} | Достигнуто максимальное количество попыток за {date_from} - {date_to}")

        logging.info(f"{self.account} | Завершено. Получено {all_records_count} строк за {date_from} - {date_to}")
