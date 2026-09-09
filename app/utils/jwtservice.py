"""
Сервис проверки JWT access-токенов.
"""

import logging
import jwt
from typing import Any

from app.config.settings import settings
from app.exceptions import InvalidToken


class JWTService:
    """
    Сервис для проверки подписи и зарегистрированных claims JWT.
    """

    #     _COMMON_REQUIRED_CLAIMS = (
    #         "exp",
    #         "iss",
    #         "sub",
    #         "aud",
    #         "iat",
    #         "jti",
    #         "sid",
    #         "auth_time",
    #         "token_type",
    #     )

    def __init__(self):
        self._access_key = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._auidience = settings.JWT_ACCESS_AUDIENCE
        self._issuer = settings.JWT_ISSUER

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """
        Декодировать access-токен.
        """
        # expected_kind = "access"
        # required_claims = (*self._COMMON_REQUIRED_CLAIMS, "authz_version")
        options = {
            "verify_aud": settings.JWT_ACCESS_AUDIENCE is not None,
            "verify_iss": settings.JWT_ISSUER is not None,
            # "require": list(required_claims),
        }

        payload = jwt.decode(
            token,
            self._access_key.get_secret_value(),
            algorithms=[self._algorithm],
            audience=self._auidience,
            issuer=self._issuer,
            options=options,
        )

        # if payload.get("token_type") != expected_kind:
        #     raise jwt.InvalidTokenError("unexpected token type")

        return payload


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Декодировать access JWT.
    """
    try:
        return JWTService().decode_access_token(token)
    except jwt.InvalidTokenError as e:
        logging.debug(f"Ошибка валидации токена: {e=}")
        raise InvalidToken() from e
