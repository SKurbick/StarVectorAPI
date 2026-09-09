from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.config.settings import settings
from app.exceptions import NotAuthenticatedError, InvalidToken
from app.utils.jwtservice import decode_access_token

from ..models import AccessTokenPayload

security = HTTPBearer(auto_error=False)


def _get_access_token_from_headers(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str | None:
    """
    Получить access-токен из заголовка.
    """
    return credentials.credentials if credentials else None


def _get_access_token_from_cookies(
    request: Request,
) -> str | None:
    """
    Получить access-токен из cookies.
    """
    return request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)


def _select_access_token(
    headers_token: str | None,
    cookies_token: str | None,
) -> str:
    """
    Выбрать токен из заголовка с приоритетом над cookie.
    """
    access_token = headers_token or cookies_token

    if not access_token:
        raise NotAuthenticatedError()

    return access_token


def _require_access_token(
    headers_token: Annotated[str | None, Depends(_get_access_token_from_headers)],
    cookies_token: Annotated[str | None, Depends(_get_access_token_from_cookies)],
) -> str:
    """
    Получить access-token.

    Если токена нет, выбрасывается исключение NotAuthenticated.
    """
    if isinstance(headers_token, str) and not headers_token:
        raise NotAuthenticatedError()

    return _select_access_token(headers_token, cookies_token)


def _decode_access_token(access_token: str) -> AccessTokenPayload:
    """
    Декодировать и валидировать access-токен.
    """
    try:
        payload = decode_access_token(access_token)
        return AccessTokenPayload.model_validate(payload)
    except (InvalidToken, ValidationError, ValueError) as e:
        raise NotAuthenticatedError() from e


def get_access_token(
    access_token: Annotated[str, Depends(_require_access_token)],
) -> AccessTokenPayload:
    """
    Получить объект данных access-токена.
    """
    return _decode_access_token(access_token)
