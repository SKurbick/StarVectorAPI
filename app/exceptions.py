class NotAuthenticatedError(Exception):
    """
    Пользователь не аутентифицирован.
    """

    def __init__(self):
        message = "Could not validate credentials."
        super().__init__(message)


class InvalidToken(Exception):
    """
    Невалидный jwt-токен.
    """

    def __init__(self):
        message = "Failed to verify authorization token."
        super().__init__(message)


class AccessForbiddenError(Exception):
    """
    Недостаточно прав.
    """

    def __init__(self):
        message = "Could not validate permissions."
        super().__init__(message)
