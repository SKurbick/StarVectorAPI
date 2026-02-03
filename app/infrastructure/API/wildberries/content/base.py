import aiohttp

from app.infrastructure.API.rate_limiters.wb import global_wb_rate_limiter
from app.infrastructure.API.wildberries.base.client import BaseWBAPIClient


class ContentWBAPI(BaseWBAPIClient):
    """API-клиент WB для категории Контент."""

    def __init__(
            self, 
            session: aiohttp.ClientSession, 
            account_name: str, 
    ):
        base_url = "https://content-api.wildberries.ru"
        rate_limiter = global_wb_rate_limiter.get_content_rate_limiter(account_name)
        super().__init__(session, account_name, base_url, rate_limiter)
