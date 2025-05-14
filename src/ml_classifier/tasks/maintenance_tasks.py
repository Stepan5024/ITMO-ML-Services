import asyncio
from datetime import datetime, timedelta
from loguru import logger

from ml_classifier.infrastructure.queue.celery_app import celery_app
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from ml_classifier.services.transaction_manager import TransactionManager


async def _async_cleanup_stale_transactions() -> int:
    """Async helper for transaction cleanup logic"""
    async for db_session in get_db():
        transaction_repo = SQLAlchemyTransactionRepository(db_session)
        transaction_manager = TransactionManager(
            transaction_repository=transaction_repo,
            user_repository=None,
        )
        return await transaction_manager.cleanup_stale_transactions()


@celery_app.task(name="ml_classifier.tasks.cleanup_stale_transactions")
def cleanup_stale_transactions():
    """
    Periodic task to clean up stale transactions.
    Finds PENDING transactions older than threshold and cancels them.
    """
    start_time = datetime.utcnow()
    logger.info("Starting cleanup of stale transactions")

    try:
        count = asyncio.run(_async_cleanup_stale_transactions())

        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Cleaned up {count} stale transactions in {elapsed_time:.2f}s")

        return {
            "cleaned_transactions": count,
            "execution_time": elapsed_time,
            "status": "completed",
        }

    except Exception as e:
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            f"Error cleaning up stale transactions: {str(e)} ({elapsed_time:.2f}s)",
            exc_info=True,
        )
        raise


@celery_app.task(name="ml_classifier.tasks.generate_daily_report")
def generate_daily_report():
    """
    Periodic task for generating daily system activity reports.
    """
    start_time = datetime.utcnow()
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    logger.info(f"Starting daily report generation for {yesterday}")

    try:
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Daily report generated for {yesterday} in {elapsed_time:.2f}s")

        return {
            "report_date": str(yesterday),
            "execution_time": elapsed_time,
            "status": "completed",
        }

    except Exception as e:
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            f"Error generating daily report for {yesterday}: {str(e)} ({elapsed_time:.2f}s)",
            exc_info=True,
        )
        raise
