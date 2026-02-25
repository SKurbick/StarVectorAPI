from fastapi import Depends

from aiohttp import ClientSession

from app.dependencies.http_session import get_wb_http_session
from app.infrastructure.marketplace_cards_api import MarketplaceCardsAPI
from app.service.marketplace_cards import MarketplaceCardsService


def get_marketplace_cards_app(session: ClientSession = Depends(get_wb_http_session)) -> MarketplaceCardsAPI:
    """Получение пула соединений из состояния приложения."""
    return MarketplaceCardsAPI(session=session)


def get_marketplace_cards_service(
        marketplace_cards_app: MarketplaceCardsAPI = Depends(get_marketplace_cards_app)
) -> MarketplaceCardsService:
    return MarketplaceCardsService(
        marketplace_cards_api=marketplace_cards_app
    )
