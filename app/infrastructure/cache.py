import asyncio
import hashlib
import json
import logging
from typing import Callable, Awaitable
from functools import wraps
import inspect

from redis.asyncio import Redis
from fastapi import HTTPException, status

from app.infrastructure.redis_client import redis_client


logger = logging.getLogger(__name__)


def redis_cache_async(
    redis_instance: Redis = None,
    ttl: int = 60,
    lock_ttl: int = 70,
    wait_for_result_ttl: int = 75,
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
            redis_cl = redis_instance

            if redis_cl is None:
                try:
                    redis_cl = redis_client.get_client()
                except RuntimeError:
                    await redis_client.connect()
                    redis_cl = redis_client.get_client()

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            filtered_args = []

            for name, value in bound_args.arguments.items():
                if name in exclude_args:
                    continue

                filtered_args.append(f"{name}={value}")


            key_parts = [func.__module__, func.__qualname__, str(filtered_args)]
            cache_key = f"{key_prefix}:{hashlib.md5(":".join(key_parts).encode()).hexdigest()}"

            try:
                cached_result = await redis_cl.get(cache_key)

                if cached_result:
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Ошибка получения кэша для ключа '{cache_key}': {e}")

            lock_key = f"lock:{cache_key}"
            lock = redis_cl.lock(lock_key, timeout=lock_ttl)

            acquired = await lock.acquire(blocking=False)

            if acquired:
                try:
                    logger.info(f"Получен Lock для ключа for key: {lock_key}, выполнение '{func.__qualname__}'")
                    result = await func(*args, **kwargs)

                    await redis_cl.setex(cache_key, ttl, json.dumps(result, ensure_ascii=False))
                    logger.info(f"Записан кеш для '{func.__qualname__}', key: {cache_key}, ttl: {ttl}")

                    return result
                except Exception as e:
                    logger.warning(f"Ошибка установки кэша для ключа '{cache_key}': {e}")
                finally:
                    await lock.release()
                    logger.info(f"Освобождаем Lock: {lock_key}")
            else:
                # Блокировка занята. Ждём освобождения и пробуем получить из кэша
                logger.info(f"Блокировка занята: {lock_key}, ожидание результата из кэша...")

                for _ in range(int(wait_for_result_ttl / 0.5)): # Проверяем кэш каждые 0.5 сек
                    await asyncio.sleep(0.5)

                    cached_result = await redis_cl.get(cache_key)

                    if cached_result:
                        logger.info(f"Получение данных из кэша после ожидания блокировки, key: {cache_key}")
                        return json.loads(cached_result)

                logger.error(f"Истекло время ожидания результата после разблокировки ключа: {lock_key}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Timed out waiting for report generation by another request."
                )

        return wrapper

    return decorator
