from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import init_db, close_db
from app.api.endpoints import (article_router,card_data_router, price_discount_router,
                               orders_revenues_router, unit_economics_router, net_profit_router, percent_by_tax_router)
from contextlib import asynccontextmanager
import uvicorn
from app.config.settings import settings


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
app.include_router(orders_revenues_router, prefix="/api")
app.include_router(unit_economics_router, prefix="/api")
app.include_router(net_profit_router, prefix="/api")
app.include_router(percent_by_tax_router, prefix="/api")

origins = [
    "http://192.168.2.49:5173"
    f"http://{settings.FRONTEND_API_ADDRESS}:{settings.FRONTEND_PORT}"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Список разрешённых origin
    allow_credentials=True,  # Разрешить передачу cookies и авторизационных данных
    allow_methods=["*"],  # Разрешить все HTTP методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)
if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.APP_IP_ADDRESS, port=settings.APP_PORT, reload=True)
