class WBAPIError(Exception):
    """Базовое исключение для ошибок WB API."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class WBRateLimitError(WBAPIError):
    """Ошибка превышения лимитов."""
    pass


class WBNotFoundError(WBAPIError):
    """Ресурс не найден (404)."""
    pass


class WBClientError(WBAPIError):
    """Ошибка клиента (400-499)."""
    pass


class WBServerError(WBAPIError):
    """Ошибка сервера (500-599)."""
    pass
