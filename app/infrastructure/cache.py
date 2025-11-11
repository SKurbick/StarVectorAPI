import hashlib
import json
import logging
from typing import Callable, Awaitable
from functools import wraps
import inspect

from redis.asyncio import Redis

from app.infrastructure.redis_client import redis_client


logger = logging.getLogger(__name__)


def redis_cache_async(
    redis_instance: Redis = redis_client,
    ttl: int = 60,
    key_prefix: str = "cache",
    exclude_args=None,
):
    """
    Декоратор для кэширования асинхронных функций в Redis.
    Генерирует ключ на основе имени функции и аргументов.
    """
    exclude_args = exclude_args or set()
    exclude_args.add("self")

    def decorator(func: Callable[..., Awaitable[any]]) -> Callable[..., Awaitable[any]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> any:
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            filtered_args = []

            for name, value in bound_args.arguments.items():
                if name in exclude_args:
                    continue

                filtered_args.append(f"{name}={value}")


            key_parts = [func.__module__, func.__qualname__, str(filtered_args)]
            cache_key = f"{key_prefix}:{hashlib.md5(':'.join(key_parts).encode()).hexdigest()}"

            try:
                cached_result = await redis_instance.get(cache_key)

                if cached_result:
                    return json.loads(cached_result.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Ошибка получения кэша для ключа '{cache_key}': {e}")

            result = await func(*args, **kwargs)

            try:
                await redis_instance.setex(cache_key, ttl, json.dumps(result, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"Ошибка установки кэша для ключа '{cache_key}': {e}")

            return result

        return wrapper

    return decorator
