import logging
from typing import Optional

from aiohttp import ClientSession, TCPConnector, ClientTimeout
from aiohttp.client_exceptions import ClientError


logger = logging.getLogger(__name__)


async def init_client_session(
    timeout: int = 60,
    max_connections: int = 100,
    ssl: bool = True
) -> Optional[ClientSession]:
    """Инициализация пула HTTP-соединений для внешних запросов."""
    try:
        logger.info(
            f"Инициализация HTTP-клиента (таймаут={timeout}s, "
            f"max_connections={max_connections}, ssl={ssl})..."
        )

        connector = TCPConnector(
            limit=max_connections,
            ssl=ssl,
            keepalive_timeout=60,
            force_close=False
        )
        
        session = ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=timeout),
        )

        logger.info(f"HTTP-клиент успешно инициализирован.")
        return session

    except ClientError as e:
        logger.exception(f"Ошибка сети при инициализации HTTP-клиента: {e}")
        return None

    except Exception as e:
        logger.exception(f"Неожиданная ошибка при инициализации HTTP-клиента: {type(e).__name__}: {e}")
        return None


async def close_client_session(session: Optional[ClientSession]) -> bool:
    """Закрытие пула HTTP-соединений."""
    if session is None or session.closed:
        logger.debug("Попытка закрыть неинициализированную или уже закрытую сессию. Пропускаем.")
        return False

    try:
        logger.info(
            f"Закрытие HTTP-клиента... "
            f"(открытых соединений: {len(session.connector._conns) if session.connector else 0})"
        )
        
        await session.close()

        logger.info(
            f"HTTP-клиент успешно закрыт. "
            f"Все соединения освобождены."
        )
        return True

    except Exception as e:
        logger.exception(f"Ошибка при закрытии HTTP-клиента: {type(e).__name__}: {e}")
        return False
