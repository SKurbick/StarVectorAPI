from aiohttp import ClientSession
from fastapi import Request


def get_wb_http_session(request: Request) -> ClientSession:
    """Получение пула HTTP-соединений из состояния приложения."""
    return request.app.state.wb_session
