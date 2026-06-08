import logging

from app.infrastructure.API.rate_limiters.rate_limiter import RateLimitConfig, RateLimiter


logger = logging.getLogger(__name__)


WB_CONTENT_CARDS_UPLOAD = "/content/v2/cards/upload"
WB_CONTENT_CARDS_UPDATE = "/content/v2/cards/update"
WB_CONTENT_CARDS_ERROR_LIST = "/content/v2/cards/error/list"
WB_FINANCE_SALES_REPORTS_DATAILED = "/finance/v1/sales-reports/detailed"


class _GlobalWBRateLimiter:
    """
    Глобальный менеджер рейт-лимитеров по аккаунтам WB.
    """

    def __init__(self):
        self._content_rate_limiters: dict[str, RateLimiter] = {}
        self._finance_rate_limiters: dict[str, RateLimiter] = {}
        self._active_accounts = {}
        logger.info(f"{_GlobalWBRateLimiter.__name__} инициализирован.")

    def set_active_accounts(self, accounts: list[str]):
        """
        Добавить аккаунты, доступные для работы с WB.
        """
        self._active_accounts = {acc.capitalize() for acc in accounts}
        logger.info(f"Доступные аккаунты установлены в {_GlobalWBRateLimiter.__name__}.")

    def get_content_rate_limiter(self, account_name: str) -> RateLimiter:
        """
        Получить рейт-лимитер для эндпоинтов категории Контент.
        """
        account = account_name.capitalize()
        logger.debug(f"Получение рейт-лимитера к категории Контент Wildberries [{account}]...")

        if account not in self._active_accounts:
            raise ValueError(f"Аккаунт {account} не найден среди активных аккаунтов.")

        if account not in self._content_rate_limiters:
            rate_limit_config = RateLimitConfig(
                base_interval=0.6,
                endpoint_overrides={
                    WB_CONTENT_CARDS_UPLOAD: 6.0,
                    WB_CONTENT_CARDS_UPDATE: 6.0,
                    WB_CONTENT_CARDS_ERROR_LIST: 6.0,
                }
            )
            self._content_rate_limiters[account] = RateLimiter(limiter_name=f"{account}-wb-content", config=rate_limit_config)

        return self._content_rate_limiters[account]
    
    def get_finance_rate_limiter(self, account_name: str) -> RateLimiter:
        """
        Получить рейт-лимитер для эндпоинтов категории Финансовые отчеты.
        """
        account = account_name.capitalize()
        logger.debug(f"Получение рейт-лимитера к категории Финансовые отчеты Wildberries [{account}]...")

        if account not in self._active_accounts:
            raise ValueError(f"Аккаунт {account} не найден среди активных аккаунтов.")

        if account not in self._finance_rate_limiters:
            rate_limit_config = RateLimitConfig(
                base_interval=60.0,
                endpoint_overrides={
                    WB_FINANCE_SALES_REPORTS_DATAILED: 60.0,
                }
            )
            self._finance_rate_limiters[account] = RateLimiter(limiter_name=f"{account}-wb-finance", config=rate_limit_config)

        return self._finance_rate_limiters[account]

global_wb_rate_limiter = _GlobalWBRateLimiter()
