"""Task modules for asynchronous processing."""

# Import all tasks so they're registered with Celery
from ml_classifier.tasks.prediction_tasks import (
    execute_prediction,
    execute_batch_prediction,
)
from ml_classifier.tasks.report_tasks import (
    generate_transaction_report,
    generate_usage_report,
)
from ml_classifier.tasks.maintenance_tasks import (
    cleanup_stale_transactions,
    generate_daily_report,
)

# Export the task functions for easier imports
__all__ = [
    "execute_prediction",
    "execute_batch_prediction",
    "generate_transaction_report",
    "generate_usage_report",
    "cleanup_stale_transactions",
    "generate_daily_report",
]
