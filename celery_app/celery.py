import logging

from celery import Celery

from app.config.settings import settings


logger = logging.getLogger(__name__)


def create_celery_app():
    celery_app = Celery(
        "starvectorapi",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Europe/Moscow",
        enable_utc=True,
        result_expires=3600,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_pool='prefork',
        worker_concurrency=2,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_retry_delay=60,
        task_max_retries=3,
        worker_send_task_events=True,
        task_send_sent_event=True,
    )

    return celery_app


celery_app = create_celery_app()


celery_app.autodiscover_tasks([
    'celery_app.tasks.reset_wb_stocks_for_closed_card',
])
