import logging
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)


class MCMClient:
    """
    Клиент для проксирования запросов в MarketplaceCardsManager.
    """

    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")
        logger.info(f"MCMClient инициализирован | base_url={self.base_url}")

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None
    ) -> Any:
        """
        Внутренний метод выполнения HTTP-запроса к MCM.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug(f"Отправлен {method} запрос на {url} | params={params}")

        async with self.session.request(
            method,
            url,
            json=json_data,
            params=params,
            headers=headers
        ) as response:
            logger.debug(f"Получен {method} ответ от {url} | status={response.status}")

            content_type = response.headers.get("Content-Type", "")
            body = await response.json() if "application/json" in content_type else await response.text()

            response.raise_for_status()
            return body

    async def get(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        return await self._request("GET", path, params=params, headers=headers)

    async def post(self, path: str, json: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
        return await self._request("POST", path, json_data=json, headers=headers)

    async def put(self, path: str, json: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
        return await self._request("PUT", path, json_data=json, headers=headers)

    async def delete(self, path: str, headers: dict[str, str] | None = None) -> Any:
        return await self._request("DELETE", path, headers=headers)
