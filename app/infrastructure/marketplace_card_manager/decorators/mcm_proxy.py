import logging
import functools
from typing import Callable, TypeVar, Awaitable, cast

import aiohttp
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


T = TypeVar("T")


def mcm_proxy_handler(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Декоратор для обработки ошибок при проксировании запросов в MCM.

    Перехватывает:
    - aiohttp.ClientResponseError: маппит статус и деталь в HTTPException
    - aiohttp.ClientError: возвращает 502 Bad Gateway

    Требует, чтобы декорируемый метод принадлежал классу с методом _handle_mcm_status_error.

    Args:
        func: Асинхронный метод сервиса.

    Returns:
        Обёрнутый асинхронный метод с единой обработкой ошибок.
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs) -> T:
        method_name = func.__name__
        try:
            return await func(self, *args, **kwargs)
        except aiohttp.ClientResponseError as e:
            if hasattr(self, "_handle_mcm_status_error"):
                await self._handle_mcm_status_error(error=e, context=method_name)
            logger.error("Unhandled ClientResponseError in %s: %s", method_name, str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ошибка обработки ответа от MarketplaceCardsManager"
            ) from e
        except aiohttp.ClientError as e:
            logger.error("Network/Transport error in %s: %s", method_name, str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Сервис MarketplaceCardsManager временно недоступен"
            ) from e

    return cast(Callable[..., Awaitable[T]], wrapper)
