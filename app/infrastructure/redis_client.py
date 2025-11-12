from typing import Optional

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError

from app.config.settings import settings


class RedisClient:
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None

    def _build_pool(self) -> ConnectionPool:
        return ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            socket_timeout=settings.REDIS_TIMEOUT,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            health_check_interval=30,
            decode_responses=True,
        )

    async def connect(self) -> Redis:
        if self.client is None:
            self.pool = self._build_pool()
            self.client = Redis(connection_pool=self.pool)

            try:
                await self.client.ping()
                print(f"Redis подключён: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
            except (ConnectionError, TimeoutError) as e:
                print(f"Ошибка подключения к Redis: {e}")
                raise

        return self.client

    async def disconnect(self):
        if self.client:
            await self.client.aclose()
            self.client = None

        if self.pool:
            await self.pool.disconnect()
            self.pool = None

    def get_client(self) -> Redis:
        if self.client is None:
            raise RuntimeError("Клиент Redis не подключен. Сначала вызовите connect().")

        return self.client


redis_client = RedisClient()
