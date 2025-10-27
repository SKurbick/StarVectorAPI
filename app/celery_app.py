import asyncio

from celery import Celery

from app.infrastructure.database import init_db


celery_app = Celery(
    "wb_tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    # broker="redis://localhost:6379/0",
    # backend="redis://localhost:6379/0",
    include=["app.tasks.wb_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.on_after_configure.connect
def init_celery_db(sender=None, **kwargs):
    """Инициализировать пул БД при запуске Celery-воркера."""
    asyncio.run(init_db())
