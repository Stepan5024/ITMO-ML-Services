import asyncio
import time
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, date
import json
import csv
import io
from loguru import logger

from ml_classifier.infrastructure.queue.celery_app import celery_app
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.transaction_repository import (
    SQLAlchemyTransactionRepository,
)

from ml_classifier.infrastructure.db.repositories.task_repository import (
    SQLAlchemyTaskRepository,
)


async def _async_generate_transaction_report(
    user_uuid: UUID,
    start_date_obj: date,
    end_date_obj: date,
    report_format: str,
    task_id: str,
) -> Dict[str, Any]:
    async for db_session in get_db():
        transaction_repo = SQLAlchemyTransactionRepository(db_session)
        transactions = await transaction_repo.get_by_user_id(user_uuid)

        filtered_transactions = [
            tx
            for tx in transactions
            if start_date_obj <= tx.created_at.date() <= end_date_obj
        ]

        transaction_data = []
        for tx in filtered_transactions:
            transaction_data.append(
                {
                    "id": str(tx.id),
                    "type": tx.type.value,
                    "amount": float(tx.amount),
                    "status": tx.status.value,
                    "created_at": tx.created_at.isoformat(),
                    "completed_at": tx.completed_at.isoformat()
                    if tx.completed_at
                    else None,
                    "description": tx.description,
                }
            )

        if report_format.lower() == "json":
            report_content = json.dumps(transaction_data, indent=2)
        elif report_format.lower() == "csv":
            output = io.StringIO()
            if transaction_data:
                writer = csv.DictWriter(output, fieldnames=transaction_data[0].keys())
                writer.writeheader()
                writer.writerows(transaction_data)
            report_content = output.getvalue()
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

        return {
            "report_content": report_content,
            "format": report_format,
            "transaction_count": len(transaction_data),
            "period": {
                "start": start_date_obj.isoformat(),
                "end": end_date_obj.isoformat(),
            },
            "user_id": str(user_uuid),
            "task_id": task_id,
        }


@celery_app.task(bind=True, name="ml_classifier.tasks.generate_transaction_report")
def generate_transaction_report(
    self, user_id: str, start_date: str, end_date: str, report_format: str = "json"
) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(
        f"Starting transaction report task: user_id={user_id}, "
        f"period={start_date} to {end_date}, format={report_format}, "
        f"task_id={self.request.id}"
    )

    try:
        user_uuid = UUID(user_id)
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        result = asyncio.run(
            _async_generate_transaction_report(
                user_uuid=user_uuid,
                start_date_obj=start_date_obj,
                end_date_obj=end_date_obj,
                report_format=report_format,
                task_id=self.request.id,
            )
        )

        execution_time = time.time() - start_time
        logger.info(
            f"Transaction report completed: task_id={self.request.id}, "
            f"transactions={result['transaction_count']}, execution_time={execution_time:.3f}s"
        )

        return {**result, "execution_time": execution_time, "status": "completed"}

    except Exception as e:
        logger.error(
            f"Transaction report failed: task_id={self.request.id}, error={str(e)}",
            exc_info=True,
        )
        raise


async def _async_generate_usage_report(
    user_uuid: UUID,
    start_date_obj: date,
    end_date_obj: date,
    report_format: str,
    task_id: str,
) -> Dict[str, Any]:
    async for db_session in get_db():
        task_repo = SQLAlchemyTaskRepository(db_session)
        tasks = await task_repo.get_by_user_id(user_uuid)

        filtered_tasks = [
            task
            for task in tasks
            if start_date_obj <= task.created_at.date() <= end_date_obj
        ]

        model_usage = {}
        for task in filtered_tasks:
            model_id = str(task.model_id)
            if model_id not in model_usage:
                model_usage[model_id] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                }

            model_usage[model_id]["total_calls"] += 1
            if task.is_completed():
                model_usage[model_id]["successful_calls"] += 1
            elif task.is_failed():
                model_usage[model_id]["failed_calls"] += 1

        usage_data = [
            {
                "model_id": model_id,
                "total_calls": stats["total_calls"],
                "successful_calls": stats["successful_calls"],
                "failed_calls": stats["failed_calls"],
                "success_rate": (stats["successful_calls"] / stats["total_calls"]) * 100
                if stats["total_calls"] > 0
                else 0,
            }
            for model_id, stats in model_usage.items()
        ]

        if report_format.lower() == "json":
            report_content = json.dumps(usage_data, indent=2)
        elif report_format.lower() == "csv":
            output = io.StringIO()
            if usage_data:
                writer = csv.DictWriter(output, fieldnames=usage_data[0].keys())
                writer.writeheader()
                writer.writerows(usage_data)
            report_content = output.getvalue()
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

        return {
            "report_content": report_content,
            "format": report_format,
            "model_count": len(usage_data),
            "total_usage": sum(item["total_calls"] for item in usage_data),
            "period": {
                "start": start_date_obj.isoformat(),
                "end": end_date_obj.isoformat(),
            },
            "user_id": str(user_uuid),
            "task_id": task_id,
        }


@celery_app.task(bind=True, name="ml_classifier.tasks.generate_usage_report")
def generate_usage_report(
    self, user_id: str, start_date: str, end_date: str, report_format: str = "json"
) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(
        f"Starting usage report task: user_id={user_id}, "
        f"period={start_date} to {end_date}, format={report_format}, "
        f"task_id={self.request.id}"
    )

    try:
        user_uuid = UUID(user_id)
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        result = asyncio.run(
            _async_generate_usage_report(
                user_uuid=user_uuid,
                start_date_obj=start_date_obj,
                end_date_obj=end_date_obj,
                report_format=report_format,
                task_id=self.request.id,
            )
        )

        execution_time = time.time() - start_time
        logger.info(
            f"Usage report completed: task_id={self.request.id}, "
            f"models={result['model_count']}, execution_time={execution_time:.3f}s"
        )

        return {**result, "execution_time": execution_time, "status": "completed"}

    except Exception as e:
        logger.error(
            f"Usage report failed: task_id={self.request.id}, error={str(e)}",
            exc_info=True,
        )
        raise
