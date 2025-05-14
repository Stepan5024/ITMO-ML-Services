import asyncio
import time
from typing import Dict, List, Optional, Any
from uuid import UUID
from loguru import logger
from celery import shared_task

from ml_classifier.infrastructure.queue.celery_app import celery_app
from ml_classifier.infrastructure.ml.prediction_service import PredictionService
from ml_classifier.infrastructure.ml.model_loader import ModelLoader
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.ml_model_repository import (
    SQLAlchemyMLModelRepository,
)
from ml_classifier.infrastructure.db.repositories.ml_model_version_repository import (
    SQLAlchemyMLModelVersionRepository,
)
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.infrastructure.db.repositories.task_repository import (
    SQLAlchemyTaskRepository,
)
from ml_classifier.infrastructure.db.repositories.transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from ml_classifier.services.task_queue_service import TaskQueueService


async def _async_execute_prediction(
    user_uuid: UUID,
    model_uuid: UUID,
    data: Dict[str, Any],
    version_uuid: Optional[UUID],
    sandbox: bool,
    task_id: str,
    start_time: float,
) -> Dict[str, Any]:
    async for db_session in get_db():
        # Initialize repos and services
        user_repo = SQLAlchemyUserRepository(db_session)
        model_repo = SQLAlchemyMLModelRepository(db_session)
        version_repo = SQLAlchemyMLModelVersionRepository(db_session)
        task_repo = SQLAlchemyTaskRepository(db_session)
        transaction_repo = SQLAlchemyTransactionRepository(db_session)

        model_loader = ModelLoader(model_repo, version_repo, "models")

        prediction_service = PredictionService(
            model_loader=model_loader,
            model_repository=model_repo,
            user_repository=user_repo,
            task_repository=task_repo,
            transaction_repository=transaction_repo,
        )

        # Find the associated task if it exists
        task = None
        try:
            task = await task_repo.get_by_celery_task_id(task_id)
            if task:
                # Update task status to PROCESSING
                task.start_processing()
                await task_repo.update(task)
                logger.info(f"Task {task.id} status updated to PROCESSING")
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")

        try:
            # Execute the prediction
            result = await prediction_service.predict(
                user_id=user_uuid,
                model_id=model_uuid,
                data=data,
                version_id=version_uuid,
                sandbox=sandbox,
            )

            execution_time = time.time() - start_time
            logger.info(
                f"Prediction completed: task_id={task_id}, "
                f"execution_time={execution_time:.3f}s"
            )

            # Update task status to COMPLETED with results
            if task:
                task.complete(result)
                await task_repo.update(task)
                logger.info(f"Task {task.id} marked as COMPLETED")

            # Update queue statistics if using task queue service
            task_queue_service = TaskQueueService(task_repo)
            if task and hasattr(task, "priority") and task.waiting_time() is not None:
                task_queue_service.update_queue_stats(
                    task.priority, task.waiting_time()
                )

            return {
                "result": result,
                "execution_time": execution_time,
                "task_id": task_id,
                "model_id": str(model_uuid),
                "version_id": str(version_uuid) if version_uuid else None,
                "status": "completed",
            }
        except Exception as e:
            # Handle errors and update task status
            logger.error(f"Prediction error: {str(e)}")

            if task:
                task.fail(str(e))
                await task_repo.update(task)
                logger.info(f"Task {task.id} marked as FAILED: {str(e)}")

            # Re-raise the exception for Celery's retry mechanism to handle
            raise


@shared_task(bind=True, name="ml_classifier.tasks.execute_prediction")
def execute_prediction(
    self,
    user_id: str,
    model_id: str,
    data: Dict[str, Any],
    version_id: Optional[str] = None,
    sandbox: bool = False,
) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(
        f"Starting prediction task: user_id={user_id}, model_id={model_id}, "
        f"task_id={self.request.id}, sandbox={sandbox}"
    )

    try:
        user_uuid = UUID(user_id)
        model_uuid = UUID(model_id)
        version_uuid = UUID(version_id) if version_id else None

        result = asyncio.run(
            _async_execute_prediction(
                user_uuid=user_uuid,
                model_uuid=model_uuid,
                data=data,
                version_uuid=version_uuid,
                sandbox=sandbox,
                task_id=self.request.id,
                start_time=start_time,
            )
        )
        return result

    except Exception as e:
        logger.error(
            f"Prediction failed: task_id={self.request.id}, error={str(e)}",
            exc_info=True,
        )

        # Don't retry certain expected errors
        if not any(
            error_type in str(e)
            for error_type in [
                "InsufficientBalanceError",
                "ModelNotFoundError",
                "ValidationError",
            ]
        ):
            # For unexpected errors, retry with exponential backoff
            retry_count = self.request.retries
            max_retries = 3

            if retry_count < max_retries:
                # Calculate exponential backoff delay
                backoff_delay = 2**retry_count * 30  # 30s, 60s, 120s...
                logger.info(
                    f"Retrying task in {backoff_delay} seconds (retry {retry_count + 1}/{max_retries})"
                )
                raise self.retry(
                    exc=e, countdown=backoff_delay, max_retries=max_retries
                )

        # For expected errors or after max retries, handle gracefully
        asyncio.run(update_failed_task(self.request.id, str(e)))

        # Return a structured error response
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id,
            "model_id": model_id,
            "execution_time": time.time() - start_time,
        }


async def _async_execute_batch_prediction(
    user_uuid: UUID,
    model_uuid: UUID,
    data_list: List[Dict[str, Any]],
    version_uuid: Optional[UUID],
    sandbox: bool,
    task_id: str,
    start_time: float,
    task_instance: Any,
) -> Dict[str, Any]:
    async for db_session in get_db():
        user_repo = SQLAlchemyUserRepository(db_session)
        model_repo = SQLAlchemyMLModelRepository(db_session)
        version_repo = SQLAlchemyMLModelVersionRepository(db_session)
        task_repo = SQLAlchemyTaskRepository(db_session)
        transaction_repo = SQLAlchemyTransactionRepository(db_session)

        model_loader = ModelLoader(model_repo, version_repo, "models")

        prediction_service = PredictionService(
            model_loader=model_loader,
            model_repository=model_repo,
            user_repository=user_repo,
            task_repository=task_repo,
            transaction_repository=transaction_repo,
        )

        # Find and update task status
        task = None
        try:
            task = await task_repo.get_by_celery_task_id(task_id)
            if task:
                # Update progress information in task
                task.start_processing()
                # Store batch size in task's output_data
                if not task.output_data:
                    task.output_data = {}
                task.output_data["batch_size"] = len(data_list)
                task.output_data["processed"] = 0
                await task_repo.update(task)
        except Exception as e:
            logger.error(f"Error updating batch task status: {str(e)}")

        try:
            # For large batches, provide progress updates
            total_items = len(data_list)
            results = []
            error_count = 0

            # Process items in smaller chunks to provide progress updates
            chunk_size = min(10, total_items)
            for i in range(0, total_items, chunk_size):
                start_index = i
                end_index = i + chunk_size
                chunk = data_list[start_index:end_index]
                # Process chunk
                try:
                    chunk_result = await prediction_service.batch_predict(
                        user_id=user_uuid,
                        model_id=model_uuid,
                        data_list=chunk,
                        version_id=version_uuid,
                        sandbox=sandbox,
                    )
                    results.extend(chunk_result["results"])
                except Exception as e:
                    logger.error(
                        f"Error processing chunk {i // chunk_size + 1}: {str(e)}"
                    )
                    # Add error placeholders for the failed chunk
                    error_results = [
                        {"error": str(e), "prediction": None, "confidence": 0}
                        for _ in chunk
                    ]
                    results.extend(error_results)
                    error_count += len(chunk)

                # Update progress
                if task:
                    task.output_data["processed"] = i + len(chunk)
                    await task_repo.update(task)

                    # Report progress to Celery
                    task_instance.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + len(chunk),
                            "total": total_items,
                            "status": f"Processing batch ({i + len(chunk)}/{total_items})",
                        },
                    )

            execution_time = time.time() - start_time

            # Compile final result
            final_result = {
                "results": results,
                "execution_time_ms": int(execution_time * 1000),
                "total_items": total_items,
                "successful_items": total_items - error_count,
                "error_count": error_count,
            }

            # Update task as completed
            if task:
                task.complete(final_result)
                await task_repo.update(task)

                # Update queue statistics
                if hasattr(task, "priority") and task.waiting_time() is not None:
                    task_queue_service = TaskQueueService(task_repo)
                    task_queue_service.update_queue_stats(
                        task.priority, task.waiting_time()
                    )

            return {
                "status": "completed",
                "execution_time": execution_time,
                "task_id": task_id,
                "model_id": str(model_uuid),
                "results_summary": {
                    "total": total_items,
                    "successful": total_items - error_count,
                    "failed": error_count,
                },
            }

        except Exception as e:
            logger.error(f"Batch prediction error: {str(e)}")

            # Update task as failed
            if task:
                task.fail(f"Batch processing failed: {str(e)}")
                await task_repo.update(task)

            # Re-raise for retry mechanism
            raise


@celery_app.task(bind=True, name="ml_classifier.tasks.execute_batch_prediction")
def execute_batch_prediction(
    self,
    user_id: str,
    model_id: str,
    data_list: List[Dict[str, Any]],
    version_id: Optional[str] = None,
    sandbox: bool = False,
) -> Dict[str, Any]:
    """Execute batch predictions with progress tracking and error handling."""
    start_time = time.time()
    logger.info(
        f"Starting batch prediction task: user_id={user_id}, model_id={model_id}, "
        f"task_id={self.request.id}, items={len(data_list)}, sandbox={sandbox}"
    )

    try:
        user_uuid = UUID(user_id)
        model_uuid = UUID(model_id)
        version_uuid = UUID(version_id) if version_id else None

        result = asyncio.run(
            _async_execute_batch_prediction(
                user_uuid=user_uuid,
                model_uuid=model_uuid,
                data_list=data_list,
                version_uuid=version_uuid,
                sandbox=sandbox,
                task_id=self.request.id,
                start_time=start_time,
            )
        )
        return result

    except Exception as e:
        logger.error(
            f"Batch prediction failed: task_id={self.request.id}, error={str(e)}",
            exc_info=True,
        )

        # Handle specific known errors
        if not any(
            error_type in str(e)
            for error_type in [
                "InsufficientBalanceError",
                "ModelNotFoundError",
                "ValidationError",
            ]
        ):
            # For unexpected errors, implement a retry mechanism with backoff
            retry_count = self.request.retries
            max_retries = 2  # Lower for batch jobs since they're resource intensive

            if retry_count < max_retries:
                backoff_delay = 60 * (retry_count + 1)  # 60s, 120s
                logger.info(
                    f"Retrying batch task in {backoff_delay} seconds "
                    f"(retry {retry_count + 1}/{max_retries})"
                )
                raise self.retry(
                    exc=e, countdown=backoff_delay, max_retries=max_retries
                )

        # Update task as failed if at max retries or expected error
        asyncio.run(update_failed_task(self.request.id, str(e)))

        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id,
            "model_id": model_id,
            "execution_time": time.time() - start_time,
        }


async def update_failed_task(celery_task_id: str, error_message: str) -> None:
    """Utility function to update a failed task."""
    try:
        async for db_session in get_db():
            task_repo = SQLAlchemyTaskRepository(db_session)
            task = await task_repo.get_by_celery_task_id(celery_task_id)
            if task:
                task.fail(error_message)
                await task_repo.update(task)
                logger.info(f"Task {task.id} marked as FAILED: {error_message}")
    except Exception as e:
        logger.error(f"Error updating failed task status: {str(e)}")
