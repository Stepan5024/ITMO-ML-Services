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
from ml_classifier.services.billing_use_cases import BillingUseCase


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

        if not sandbox:
            BillingUseCase(
                transaction_repository=transaction_repo,
                user_repository=user_repo,
                pricing_service=None,  # Replace with actual pricing service
            )

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

        return {
            "result": result,
            "execution_time": execution_time,
            "task_id": task_id,
            "model_id": str(model_uuid),
            "version_id": str(version_uuid) if version_uuid else None,
            "status": "completed",
        }


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

        if not any(
            error_type in str(e)
            for error_type in [
                "InsufficientBalanceError",
                "ModelNotFoundError",
                "ValidationError",
            ]
        ):
            raise self.retry(exc=e, countdown=30)
        raise


async def _async_execute_batch_prediction(
    user_uuid: UUID,
    model_uuid: UUID,
    data_list: List[Dict[str, Any]],
    version_uuid: Optional[UUID],
    sandbox: bool,
    task_id: str,
    start_time: float,
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

        result = await prediction_service.batch_predict(
            user_id=user_uuid,
            model_id=model_uuid,
            data_list=data_list,
            version_id=version_uuid,
            sandbox=sandbox,
        )

        execution_time = time.time() - start_time
        logger.info(
            f"Batch prediction completed: task_id={task_id}, "
            f"items={len(data_list)}, execution_time={execution_time:.3f}s"
        )

        return {
            "results": result["results"],
            "execution_time": execution_time,
            "task_id": task_id,
            "model_id": str(model_uuid),
            "version_id": str(version_uuid) if version_uuid else None,
            "batch_size": len(data_list),
            "status": "completed",
        }


@celery_app.task(bind=True, name="ml_classifier.tasks.execute_batch_prediction")
def execute_batch_prediction(
    self,
    user_id: str,
    model_id: str,
    data_list: List[Dict[str, Any]],
    version_id: Optional[str] = None,
    sandbox: bool = False,
) -> Dict[str, Any]:
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

        if not any(
            error_type in str(e)
            for error_type in [
                "InsufficientBalanceError",
                "ModelNotFoundError",
                "ValidationError",
            ]
        ):
            raise self.retry(exc=e, countdown=30)
        raise
