import logging

from celery import Celery

from app.config.settings import settings


logger = logging.getLogger(__name__)


def create_celery_app():
    celery_app = Celery(
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
    )

    return celery_app


celery_client = create_celery_app()
