from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import init_db, close_db
from app.api.endpoints import article_router, card_data_router, price_discount_router
from contextlib import asynccontextmanager
import uvicorn


# Контекстный менеджер для управления жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация пула соединений при старте приложения
    pool = await init_db()
    app.state.pool = pool
    yield
    # Закрытие пула соединений при завершении работы приложения
    await close_db(pool)


# Создаем экземпляр FastAPI с использованием lifespan
app = FastAPI(lifespan=lifespan, title="VectorAPI")
app.include_router(card_data_router, prefix="/api")
app.include_router(article_router, prefix="/api")
app.include_router(price_discount_router, prefix="/api")
origins = [
    # "192.168.2.47",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Список разрешённых origin
    allow_credentials=True,  # Разрешить передачу cookies и авторизационных данных
    allow_methods=["*"],  # Разрешить все HTTP методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
