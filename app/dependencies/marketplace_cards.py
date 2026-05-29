from fastapi import Request

from app.infrastructure.marketplace_card_manager import MarketplaceCardsService


SAFE_PROXY_HEADERS = {"Authorization", "X-Correlation-ID", "Accept-Language", "X-Request-ID"}


def get_mcm_service(request: Request) -> MarketplaceCardsService:
    proxy_headers = {k: v for k, v in request.headers.items() if k in SAFE_PROXY_HEADERS}
    return MarketplaceCardsService(
        mcm_client=request.app.state.mcm_client,
        proxy_headers=proxy_headers,
    )
