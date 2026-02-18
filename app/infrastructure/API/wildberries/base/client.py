from abc import ABC
import asyncio
from enum import Enum
import logging
import json
from typing import Optional, Any

import aiohttp

from app.infrastructure.API.wildberries.base.exceptions import (
    WBAPIError,
    WBClientError,
    WBNotFoundError,
    WBRateLimitError,
    WBServerError,
)
from app.infrastructure.API.rate_limiters.rate_limiter import RateLimitConfig, RateLimiter
from app.config.settings import get_wb_tokens


logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """HTTP методы."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ResponseHandler:
    """Обработка ответов от API."""

    @staticmethod
    async def parse_json(response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Разобрать JSON ответ."""
        try:
            return await response.json()
        except json.JSONDecodeError:
            raw = await response.text()
            logger.error(f"JSON decode error. Raw: {raw[:300]}")
            raise WBAPIError("Некорректный JSON-ответ от WB.")

    @staticmethod
    async def handle_error(
        response: aiohttp.ClientResponse,
        url: str,
        account_name: str
    ) -> None:
        """Обработать ошибку из ответа."""
        status = response.status
        
        if status == 404:
            raise WBNotFoundError(
                f"[{account_name}] Ресурс не найден: {url}", 
                status_code=404
            )

        elif status == 400:
            try:
                error_data = await response.json()
                error_text = error_data.get("errorText", "Неизвестная ошибка")
            except:
                error_text = "Неизвестная ошибка"
            raise WBClientError(
                f"[{account_name}] Ошибка клиента: {error_text}", 
                status_code=400
            )

        elif 500 <= status < 600:
            raise WBServerError(
                f"[{account_name}] Серверная ошибка {status} на {url}",
                status_code=status
            )

        elif status == 429:
            raise WBRateLimitError(
                f"[{account_name}] Превышен лимит запросов на {url}",
                status_code=429
            )

        else:
            raise WBAPIError(
                f"[{account_name}] Неожиданный статус {status} на {url}",
                status_code=status
            )


class BaseWBAPIClient(ABC):
    """Базовый класс API-клиента WB."""

    _tokens = None

    def __init__(
            self,
            session: aiohttp.ClientSession,
            account_name: str,
            base_url: str,
            rate_limiter: Optional[RateLimiter] = None,
    ):
        self.session = session
        self.account_name = account_name.capitalize()
        self._base_url = base_url

        self._rate_limiter = rate_limiter or RateLimiter(config=RateLimitConfig(), limiter_name=account_name)
        self._response_handler = ResponseHandler()

    @classmethod
    async def _get_tokens(cls) -> dict[str, str]:
        if not cls._tokens:
            cls._tokens = await get_wb_tokens()

        return cls._tokens
        
    async def _get_api_token(self) -> str:
        tokens = await self._get_tokens()

        try:
            return tokens[self.account_name]
        except KeyError:
            return tokens[self.account_name.upper()]

    async def _make_request(
            self,
            endpoint: str,
            method: HTTPMethod = HTTPMethod.GET,
            payload: Optional[dict[str, any]] = None,
            timeout: Optional[float] = None,
    ) -> dict[str, any]:
        """
        Выполнить запрос к API с обработкой ошибок и повторными попытками.
        
        Args:
            endpoint: Эндпоинт относительно base_url
            method: HTTP метод
            payload: Тело запроса для методов с телом
            timeout: Таймаут запроса в секундах

        Returns:
            Словарь с данными ответа
            
        Raises:
            WBAPIError: При любой ошибке взаимодействия с API
        """
        url = f"{self._base_url}{endpoint}"
        headers = {
            "Authorization": await self._get_api_token(),
            "Content-Type": "application/json"
        }

        for attempt in range(1, self._rate_limiter.config.max_retries + 1):
            try:
                await self._rate_limiter.acquire(endpoint)
                logger.debug(
                    f"[{self.account_name}] Запрос: {method.value} {url}, "
                    f"попытка {attempt}/{self._rate_limiter.config.max_retries}"
                )

                timeout_obj = aiohttp.ClientTimeout(total=timeout) if timeout else None
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=timeout_obj
                ) as response:
                    if response.status == 200:
                        return await self._response_handler.parse_json(response)

                    await self._handle_response_error(response, url, attempt)
            except aiohttp.ClientError as e:
                logger.error(
                    f"[{self.account_name}] Ошибка клиента на {url}: {e}"
                )
                raise WBAPIError(f"Ошибка клиента: {str(e)}")
            except asyncio.TimeoutError:
                await self._handle_timeout(url, attempt)
            except WBAPIError:
                raise
            except Exception as e:
                logger.error(f"[{self.account_name}] Неожиданная ошибка: {e}")
                raise WBAPIError(f"Неожиданная ошибка: {str(e)}")

        raise WBAPIError(
            f"Превышено максимальное количество попыток "
            f"({self._rate_limiter.config.max_retries}) для {url}"
        )

    async def _handle_response_error(
        self,
        response: aiohttp.ClientResponse,
        url: str,
        attempt: int,
    ) -> None:
        """Обработать ошибку из ответа сервера."""
        status = response.status
        
        if status == 429:
            wait_time = 5 * attempt
            logger.warning(
                f"[{self.account_name}] Rate limit на {url}. "
                f"Ждем {wait_time}с..."
            )
            await asyncio.sleep(wait_time)
            return
        elif 500 <= status < 600:
            wait_time = min(
                self._rate_limiter.config.backoff_base ** (attempt - 1),
                self._rate_limiter.config.max_backoff
            )
            logger.warning(
                f"[{self.account_name}] Серверная ошибка {status} на {url}. "
                f"Попытка {attempt}/{self._rate_limiter.config.max_retries}. "
                f"Ждем {wait_time}с..."
            )
            await asyncio.sleep(wait_time)
            return
        else:
            await self._response_handler.handle_error(
                response, url, self.account_name
            )
    
    async def _handle_timeout(
        self,
        url: str,
        attempt: int,
    ) -> None:
        """Обработать таймаут."""
        wait_time = min(
            self._rate_limiter.config.backoff_base ** (attempt - 1),
            self._rate_limiter.config.max_backoff
        )
        logger.warning(
            f"[{self.account_name}] Таймаут на {url}. "
            f"Попытка {attempt}/{self._rate_limiter.config.max_retries}. "
            f"Ждем {wait_time}с..."
        )
        await asyncio.sleep(wait_time)
