from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import sopost_router
from infrastructure.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация пула соединений при старте приложения
    pool = await init_db()
    app.state.pool = pool

    yield
    # Закрытие пула соединений при завершении работы приложения
    await close_db(pool)


origins = [
    "localhost",
]


app = FastAPI(lifespan=lifespan, title="SopostAPI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Список разрешённых origin
    allow_credentials=True,  # Разрешить передачу cookies и авторизационных данных
    allow_methods=["*"],  # Разрешить все HTTP методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

app.include_router(sopost_router)
