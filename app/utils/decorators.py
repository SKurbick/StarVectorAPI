import logging
from functools import wraps
from fastapi import HTTPException


logger = logging.getLogger(__name__)


def error_handler_http(
        status_code: int = 500,
        message: str = 'Internal server error',
        exceptions: tuple = (Exception,)
):
    """Декоратор для поднятия HTTPException при обнаружении исключения.

    :pparam status_code: возвращаемый HTTP статус код при исключении.
    :param message: возвращаемое сообщение при исключении.
    :param exceptions: кортеж обрабатываемых исключений.
    """

    def decorator(func):
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as error:
                logger.error('Error in %s: %s', func.__name__, error)
                raise HTTPException(status_code=status_code, detail=message)

        return wrapper
    
    return decorator