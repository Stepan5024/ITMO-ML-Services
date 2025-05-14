"""Classification API controller."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body, status
from pydantic import BaseModel, Field, validator
from starlette.responses import JSONResponse

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.ml_model_repository import (
    SQLAlchemyMLModelRepository,
)
from ml_classifier.infrastructure.db.repositories.task_repository import (
    SQLAlchemyTaskRepository,
)
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.services.task_queue_service import TaskQueueService
from ml_classifier.services.task_use_cases import TaskUseCase

router = APIRouter(prefix="/api/v1", tags=["classification"])


class ClassificationRequest(BaseModel):
    """Request model for text classification."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Текст отзыва для классификации",
        examples=[
            "Отличный курс! Преподаватель объяснял материал очень понятно и интересно."
        ],
    )
    model_id: Optional[UUID] = None
    version_id: Optional[UUID] = None
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    async_execution: bool = False

    @validator("priority")
    def validate_priority(cls, v):
        """Validate priority levels."""
        if v not in ["low", "normal", "high"]:
            raise ValueError("Priority must be one of: low, normal, high")
        return v


class BatchClassificationRequest(BaseModel):
    """Request model for batch text classification."""

    texts: list[str] = Field(..., min_items=1, max_items=100)
    model_id: Optional[UUID] = None
    version_id: Optional[UUID] = None
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    async_execution: bool = True


class ClassificationResponse(BaseModel):
    """Response model for immediate classification results."""

    sentiment: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    categories: list[str] = []
    execution_time_ms: int


class AsyncTaskResponse(BaseModel):
    """Response model for asynchronous task creation."""

    task_id: UUID
    status: str
    estimated_completion_time: Optional[str] = None


# Dependency injection
async def get_model_repository(session=Depends(get_db)) -> MLModelRepository:
    """Get model repository instance."""
    return SQLAlchemyMLModelRepository(session)


async def get_task_use_case(
    session=Depends(get_db),
    model_repo=Depends(get_model_repository),
) -> TaskUseCase:
    """Get task use case instance."""
    task_repo = SQLAlchemyTaskRepository(session)
    task_queue_service = TaskQueueService(task_repo)
    return TaskUseCase(task_repo, model_repo, task_queue_service)


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    responses={
        200: {"description": "Успешная классификация"},
        400: {"description": "Ошибка в запросе"},
        401: {"description": "Ошибка аутентификации"},
        402: {"description": "Недостаточно средств на счете"},
        404: {"description": "Модель не найдена"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def classify_text(
    request: ClassificationRequest = Body(
        ...,
        example={
            "text": "Отличный курс! Преподаватель объяснял материал очень понятно и интересно.",
            "model_id": None,
            "version_id": None,
            "priority": "normal",
            "async_execution": False,
        },
    ),
    current_user: User = Depends(get_current_active_user),
    task_use_case: TaskUseCase = Depends(get_task_use_case),
    db_session=Depends(get_db),
):
    """
    Классифицирует текст отзыва с использованием моделей машинного обучения.

    Для коротких текстов (до 1000 символов) при async_execution=false возвращает
    немедленный результат классификации.

    Для более длинных текстов или при async_execution=true создает асинхронную задачу
    и возвращает информацию о ней.

    ### Параметры:
    - **text**: Текст отзыва для анализа
    - **model_id**: ID конкретной модели для использования (опционально)
    - **version_id**: ID версии модели для использования (опционально)
    - **priority**: Приоритет обработки (low, normal, high)
    - **async_execution**: Выполнять обработку асинхронно

    ### Возвращает:
    - Результат классификации или информацию об асинхронной задаче
    """
    if not request.async_execution and len(request.text) <= 1000:
        try:
            # Создаем сервисы напрямую вместо вызова другого контроллера
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
            from ml_classifier.infrastructure.ml.model_loader import ModelLoader
            from ml_classifier.infrastructure.ml.prediction_service import (
                PredictionService,
            )

            # Инициализируем репозитории
            model_repo = SQLAlchemyMLModelRepository(db_session)
            version_repo = SQLAlchemyMLModelVersionRepository(db_session)
            user_repo = SQLAlchemyUserRepository(db_session)
            task_repo = SQLAlchemyTaskRepository(db_session)
            transaction_repo = SQLAlchemyTransactionRepository(db_session)

            # Проверяем наличие моделей в БД
            if request.model_id:
                model = await model_repo.get_by_id(request.model_id)
                if not model:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Model with ID {request.model_id} not found",
                    )
            else:
                # Если модель не указана, проверяем есть ли активные модели
                active_models = await model_repo.get_active_models()
                if not active_models:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No active models found in the database",
                    )

            # Инициализируем сервисы
            model_loader = ModelLoader(
                model_repository=model_repo,
                model_version_repository=version_repo,
                model_storage_path="models",
            )
            prediction_service = PredictionService(
                model_loader=model_loader,
                model_repository=model_repo,
                user_repository=user_repo,
                task_repository=task_repo,
                transaction_repository=transaction_repo,
            )

            # Выполняем предсказание
            result = await prediction_service.predict(
                user_id=current_user.id,
                model_id=request.model_id,
                data={"text": request.text},
                version_id=request.version_id,
                sandbox=False,
            )
            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during prediction: {str(e)}",
            )

    success, message, task = await task_use_case.create_task(
        user_id=current_user.id,
        model_id=request.model_id,
        input_data={"text": request.text},
        priority=request.priority,
        model_version_id=request.version_id,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    wait_time = task_use_case.task_queue_service.estimate_waiting_time(request.priority)

    response = AsyncTaskResponse(
        task_id=task.id, status=task.status.value, estimated_completion_time=wait_time
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.dict(),
        headers={"Location": f"/api/v1/tasks/{task.id}"},
    )


@router.post("/classify-batch", response_model=AsyncTaskResponse)
async def classify_batch(
    request: BatchClassificationRequest,
    current_user: User = Depends(get_current_active_user),
    task_use_case: TaskUseCase = Depends(get_task_use_case),
):
    """
    Submit a batch of texts for classification.

    This endpoint always creates an asynchronous task.
    """
    input_data = {"texts": request.texts, "batch_size": len(request.texts)}

    success, message, task = await task_use_case.create_task(
        user_id=current_user.id,
        model_id=request.model_id,
        input_data=input_data,
        priority=request.priority,
        model_version_id=request.version_id,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    wait_time = task_use_case.task_queue_service.estimate_waiting_time(request.priority)
    wait_time_sec = wait_time * len(request.texts) / 10

    from datetime import datetime, timedelta

    estimated_completion = (
        datetime.utcnow() + timedelta(seconds=wait_time_sec)
    ).isoformat()

    return AsyncTaskResponse(
        task_id=task.id,
        status=task.status.value,
        estimated_completion_time=estimated_completion,
    )
