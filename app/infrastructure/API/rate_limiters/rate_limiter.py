import asyncio
from collections import defaultdict
from dataclasses import dataclass
import logging
import time
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Конфигурация рейт-лимитинга."""

    base_interval: float = 0.2
    safety_margin: float = 1.2
    endpoint_overrides: Optional[dict[str, float]] = None
    max_retries: int = 3
    backoff_base: float = 2.0
    max_backoff: float = 10.0


class RateLimiter:
    """Управление рейт-лимитами для запросов."""

    def __init__(
        self,
        config: RateLimitConfig,
        limiter_name: str = "default",
        locks: Optional[defaultdict[asyncio.Lock]] = None,
        last_request_times: Optional[defaultdict[float]] = None,
    ):
        self.limiter_name = limiter_name.capitalize()
        self.config = config
        self._locks = locks or defaultdict(asyncio.Lock)
        self._last_request_times = last_request_times or defaultdict(float)

    def _get_interval(self, endpoint: str) -> float:
        """Получить интервал для эндпоинта."""
        raw_interval = self.config.endpoint_overrides.get(
            endpoint, self.config.base_interval
        ) if self.config.endpoint_overrides else self.config.base_interval
        return raw_interval * self.config.safety_margin

    def _get_lock_key(self, endpoint: str) -> str:
        """Получить ключ для блокировки."""
        if self.config.endpoint_overrides and endpoint in self.config.endpoint_overrides:
            return endpoint
        return "default"

    async def acquire(self, endpoint: str) -> None:
        """Дождаться разрешения на запрос."""
        lock_key = self._get_lock_key(endpoint)
        interval = self._get_interval(endpoint)
        
        async with self._locks[lock_key]:
            now = time.monotonic()
            elapsed = now - self._last_request_times[lock_key]
            
            if elapsed < interval:
                delay = interval - elapsed
                logger.debug(f"[{self.limiter_name}] Задержка рейт-лимитинга: {delay:.2f}с для {endpoint}")
                await asyncio.sleep(delay)
            
            self._last_request_times[lock_key] = time.monotonic()
