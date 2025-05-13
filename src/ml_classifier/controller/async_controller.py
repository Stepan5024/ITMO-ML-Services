"""Контроллер для асинхронных операций с моделями."""
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.tasks.prediction_tasks import (
    execute_prediction,
    execute_batch_prediction,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/async", tags=["async-operations"])


class TextInput(BaseModel):
    """Модель для текстового ввода."""

    text: str
    async_execution: bool = True


class BatchTextInput(BaseModel):
    """Модель для пакетного текстового ввода."""

    items: List[TextInput]
    async_execution: bool = True


class AsyncTaskResponse(BaseModel):
    """Модель ответа для асинхронных задач."""

    task_id: str
    status: str
    message: str


@router.post("/predict/{model_id}", response_model=AsyncTaskResponse)
async def async_predict(
    model_id: UUID = Path(..., description="ID модели для использования"),
    input_data: TextInput = Body(..., description="Входные данные для предсказания"),
    version_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Запускает асинхронное предсказание с использованием указанной модели.

    Задача будет обработана в фоновом режиме, а результат можно будет получить по ID задачи.
    """
    try:
        # Создаем задачу Celery для выполнения предсказания
        task = execute_prediction.delay(
            user_id=str(current_user.id),
            model_id=str(model_id),
            data={"text": input_data.text},
            version_id=str(version_id) if version_id else None,
            sandbox=False,
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": "Prediction task submitted successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting prediction task: {str(e)}",
        )


@router.post("/batch-predict/{model_id}", response_model=AsyncTaskResponse)
async def async_batch_predict(
    model_id: UUID = Path(..., description="ID модели для использования"),
    input_data: BatchTextInput = Body(
        ..., description="Список текстов для предсказания"
    ),
    version_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Запускает асинхронное пакетное предсказание с использованием указанной модели.

    Задача будет обработана в фоновом режиме, а результат можно будет получить по ID задачи.
    """
    try:
        # Подготавливаем данные для пакетного предсказания
        data_list = [{"text": item.text} for item in input_data.items]

        # Создаем задачу Celery для выполнения пакетного предсказания
        task = execute_batch_prediction.delay(
            user_id=str(current_user.id),
            model_id=str(model_id),
            data_list=data_list,
            version_id=str(version_id) if version_id else None,
            sandbox=False,
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Batch prediction task with {len(data_list)} items submitted successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting batch prediction task: {str(e)}",
        )
