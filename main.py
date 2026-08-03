import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.infrastructure.API.rate_limiters.wb import global_wb_rate_limiter
from app.infrastructure.redis_client import redis_client
from app.infrastructure.http_client import init_client_session, close_client_session
from app.infrastructure.database import (
    init_postgres_db,
    close_postgres_db,
    init_clickhouse_client,
    close_clickhouse_client
)
from app.api.endpoints import (
    article_router,
    card_data_router,
    price_discount_router,
    favicon_router,
    turnover_router,
    orders_revenues_router,
    unit_economics_router,
    net_profit_router,
    percent_by_tax_router,
    stocks_quantity_router,
    # product_router,
    fin_reports_router,
    sales_router,
    penalties_router,
    # close_card_router,
    # open_card_router,
    competitors_prices_router,
    orders_history_router,
    product_note_router,
    # subject_data_router,
    # product_cards_router,
    ic_net_profit_router,
    sales_management_router,
    # seller_account_router,
    analytics_router,
    # wb_specifications_router,
)

from app.config.settings import settings, get_wb_tokens

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


# Контекстный менеджер для управления жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация соединений с базами данных при старте приложения
    async with asyncio.TaskGroup() as task_group:
        postgres_task = task_group.create_task(init_postgres_db())
        clickhouse_task = task_group.create_task(init_clickhouse_client())
        wb_session = task_group.create_task(init_client_session())
        # task_group.create_task(redis_client.connect())
        tokens = task_group.create_task(get_wb_tokens())
    
    # Добавление доступных аккаунтов WB в рейт-лимитер
    global_wb_rate_limiter.set_active_accounts(accounts=list(tokens.result().keys()))
    app.state.pool = postgres_task.result()
    app.state.clickhouse_client = clickhouse_task.result()
    app.state.wb_session = wb_session.result()
    yield
    # Закрытие соединений c базами данных при завершении работы приложения
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(close_postgres_db(app.state.pool))
        task_group.create_task(close_clickhouse_client(app.state.clickhouse_client))
        # task_group.create_task(redis_client.disconnect())
        task_group.create_task(close_client_session(app.state.wb_session))


# Создаем экземпляр FastAPI с использованием lifespan
app = FastAPI(lifespan=lifespan, title="VectorAPI")

base_router = APIRouter(prefix="/api")

base_router.include_router(turnover_router)
base_router.include_router(card_data_router)
base_router.include_router(article_router)
base_router.include_router(price_discount_router)
base_router.include_router(orders_revenues_router)
base_router.include_router(unit_economics_router)
base_router.include_router(net_profit_router)
base_router.include_router(percent_by_tax_router)
base_router.include_router(stocks_quantity_router)
base_router.include_router(fin_reports_router)
base_router.include_router(penalties_router)
base_router.include_router(sales_router)
base_router.include_router(competitors_prices_router)
base_router.include_router(orders_history_router)
# base_router.include_router(subject_data_router)
base_router.include_router(product_note_router)
base_router.include_router(ic_net_profit_router)
base_router.include_router(sales_management_router)
base_router.include_router(analytics_router)
# base_router.include_router(seller_account_router)
# base_router.include_router(product_router)
# base_router.include_router(product_cards_router)
# base_router.include_router(open_card_router)
# base_router.include_router(close_card_router)
# base_router.include_router(wb_specifications_router)

app.include_router(base_router)
app.include_router(favicon_router)

origins = [
    # "http://192.168.2.49:5173",
    "*",  # временное решение
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
