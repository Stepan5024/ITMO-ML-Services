from celery import Celery
import os
from loguru import logger

from celery.schedules import crontab

# Загрузка настроек
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_RESULT_DB = int(os.getenv("REDIS_RESULT_DB", 1))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Формирование строки подключения
BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
)
RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULT_DB}',
)

logger.info(f"Configuring Celery with broker: {BROKER_URL}")

# Инициализация Celery
celery_app = Celery("ml_classifier")

# Настройка Celery
celery_app.conf.update(
    broker_url=BROKER_URL,
    result_backend=RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 минут
    task_soft_time_limit=540,  # 9 минут
    worker_max_tasks_per_child=200,  # перезапуск воркера после 200 задач
    worker_prefetch_multiplier=1,  # количество задач, загружаемых воркером за раз
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_acks_late=True,  # подтверждение после выполнения
    task_reject_on_worker_lost=True,  # перезапуск задачи при потере воркера
    task_ignore_result=False,  # сохранение результатов
    # Настройки retry
    task_default_retry_delay=30,  # 30 секунд между повторами
    task_max_retries=3,  # максимум 3 повторные попытки
    # Настройки периодических задач
    beat_schedule={
        "cleanup-stale-transactions": {
            "task": "ml_classifier.tasks.cleanup_stale_transactions",
            "schedule": crontab(minute="*/15"),  # Каждые 15 минут
        },
        "generate-daily-report": {
            "task": "ml_classifier.tasks.generate_daily_report",
            "schedule": crontab(hour=3, minute=0),  # Каждый день в 3 утра
        },
    },
)

# Автоматическое обнаружение и регистрация задач
celery_app.autodiscover_tasks(["ml_classifier.tasks"])
