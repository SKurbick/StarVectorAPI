import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.domain.models import UserPermissions
from app.utils.jwtservice import JWTService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_info_from_token(
        token: str = Depends(oauth2_scheme),
) -> UserPermissions:
    #pylint: disable = raise-missing-from
    """Декодировка токена и возврат ответа в виде пользователя"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = JWTService().decode_token(token, "ACCESS")
        if payload:
            return UserPermissions(**payload)
    except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError):
        raise credentials_exception
