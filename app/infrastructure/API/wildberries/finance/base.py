import aiohttp

from app.infrastructure.API.rate_limiters.wb import global_wb_rate_limiter
from app.infrastructure.API.wildberries.base.client import BaseWBAPIClient


class FinanceWBAPI(BaseWBAPIClient):
    """
    API-клиент WB для категории Финансовые отчеты.
    """

    def __init__(
            self, 
            session: aiohttp.ClientSession, 
            account_name: str, 
    ):
        base_url = "https://finance-api.wildberries.ru/api"
        rate_limiter = global_wb_rate_limiter.get_finance_rate_limiter(account_name)
        super().__init__(session, account_name, base_url, rate_limiter)
