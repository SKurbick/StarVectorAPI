import logging
import aiohttp
from fastapi import HTTPException, status

from app.infrastructure.marketplace_card_manager.clients import MCMClient
from app.infrastructure.marketplace_card_manager.decorators.mcm_proxy import mcm_proxy_handler
from app.infrastructure.marketplace_card_manager.schemas import (
    CloseCardPreviewRequest,
    CloseCardsRequest,
    OpenCardsRequest,
)

logger = logging.getLogger(__name__)


_MCM_TO_CRM_STATUS = {
    400: status.HTTP_400_BAD_REQUEST,
    401: status.HTTP_401_UNAUTHORIZED,
    403: status.HTTP_403_FORBIDDEN,
    404: status.HTTP_404_NOT_FOUND,
    422: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


class MarketplaceCardsService:
    """
    Сервис проксирования запросов к MCM.
    """

    URL_HEALTH = "/api/health"
    URL_GET_PRODUCT_SPECIFICATIONS = "/api/v0/deprecated/products/{id}/wb/specifications"
    URL_POST_CLOSE_CARDS_PREVIEW = "/api/v0/deprecated/cards/statuses/close/preview"
    URL_POST_CLOSE_CARDS = "/api/v0/deprecated/cards/statuses/close"
    URL_POST_OPEN_CARDS = "/api/v0/deprecated/cards/statuses/open"
    
    def __init__(
            self,
            mcm_client: MCMClient,
            proxy_headers: dict[str, str],
    ):
        self._mcm_client = mcm_client
        self._proxy_headers = proxy_headers

    @mcm_proxy_handler
    async def check_health(self) -> dict[str, str]:
        """
        Проверить состояние MCM.
        """
        logger.info("Проверка состояния сервиса MCM")
        data = await self._mcm_client.get(path=self.URL_HEALTH)
        logger.debug("Запрос на проверку состояния MCM прошел успешно: data=%s", data)
        return data

    @mcm_proxy_handler
    async def get_product_wb_specifications(self, product_id: str):
        """
        Получить спецификации WB для товара.
        """
        logger.info(f"Получение спецификаций товара: product_id={product_id}")
        data = await self._mcm_client.get(
            path=self.URL_GET_PRODUCT_SPECIFICATIONS.format(id=product_id),
            headers=self._proxy_headers,
        )
        logger.debug("Запрос на получение спецификаций товара MCM прошел успешно: data=%s", data)
        return data

    @mcm_proxy_handler
    async def close_cards_preview(self, data: CloseCardPreviewRequest):
        """
        Получить информацию о карточках к закрытию.
        """
        logger.info(f"Получение информации о карточках к закрытию: data={data.__repr__()}")
        result = await self._mcm_client.post(
            self.URL_POST_CLOSE_CARDS_PREVIEW, 
            json=data.model_dump(), 
            headers=self._proxy_headers,
        )
        logger.info("Запрос на получение карточек к закрытию прошел успешно")
        return result

    @mcm_proxy_handler
    async def close_cards(self,data: CloseCardsRequest):
        """
        Закрыть карточки товаров, готовые к закрытию.
        """
        logger.info(f"Закрытие карточек товаров: data={data.__repr__()}")
        result = await self._mcm_client.post(
            self.URL_POST_CLOSE_CARDS, 
            json=data.model_dump(), 
            headers=self._proxy_headers,
        )
        logger.info("Запрос на закрытие карточек прошел успешно.")
        return result
    
    @mcm_proxy_handler
    async def open_cards(self, data: OpenCardsRequest):
        """
        Открыть карточки товаров.
        """
        logger.info(f"Открытие карточек товаров: data={data.__repr__()}")
        result = await self._mcm_client.post(
            self.URL_POST_OPEN_CARDS, 
            json=data.model_dump(), 
            headers=self._proxy_headers,
        )
        logger.info("Запрос на открытие карточек прошел успешно.")
        return result

    async def _handle_mcm_status_error(
            self, 
            error: aiohttp.ClientResponseError, 
            context: str
    ) -> None:
        """
        Маппинг HTTP-ошибок от MCM в FastAPI HTTPException.
        Вызывается декоратором mcm_proxy_handler.

        Args:
            error: Исключение aiohttp с кодом статуса.
            context: Имя метода, в котором произошла ошибка.
        """
        logger.warning("MCM ответил %d в %s | details=%s", error.status, context, str(error))
        mapped_status = _MCM_TO_CRM_STATUS.get(error.status, status.HTTP_502_BAD_GATEWAY)
        raise HTTPException(status_code=mapped_status, detail=error.message) from error
