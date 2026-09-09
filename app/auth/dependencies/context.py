from typing import Annotated

from fastapi import Depends

from ..models import AccessTokenPayload, UserRequestContext
from ..resolver import resolve_permissions

from .tokens import get_access_token


def get_user_context(
    access_token: Annotated[AccessTokenPayload | None, Depends(get_access_token)],
) -> UserRequestContext:
    """
    Получить контекст пользователя из проверенного access-токена.
    """
    return UserRequestContext(
        user_id=access_token.resolved_user_id,
        is_superuser=False,
        permissions=resolve_permissions(access_token),
    )
