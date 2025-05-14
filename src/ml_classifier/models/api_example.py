"""Примеры для API документации."""
from datetime import datetime, timedelta

LOGIN_REQUEST_EXAMPLE = {"username": "user@example.com", "password": "SecureP@ss123"}

LOGIN_RESPONSE_EXAMPLE = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
}

REGISTER_REQUEST_EXAMPLE = {
    "email": "new_user@example.com",
    "password": "SecureP@ss123",
    "full_name": "Иван Иванов",
}

# Примеры для классификации
CLASSIFICATION_REQUEST_EXAMPLE = {
    "text": "Отличный курс! Преподаватель объяснял материал очень понятно и интересно."
}

CLASSIFICATION_RESPONSE_EXAMPLE = {
    "prediction": "positive",
    "confidence": 0.92,
    "categories": ["quality", "instructor"],
    "execution_time_ms": 45,
}

BATCH_CLASSIFICATION_REQUEST_EXAMPLE = {
    "texts": [
        "Преподаватель объяснял материал очень понятно",
        "Курс слишком сложный, много непонятного материала",
        "Хорошая программа курса, но слишком высокая стоимость",
    ],
    "model_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "priority": "normal",
    "async_execution": True,
}

TRANSACTION_RESPONSE_EXAMPLE = {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "type": "deposit",
    "amount": 100.0,
    "status": "completed",
    "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
    "completed_at": datetime.utcnow().isoformat(),
    "description": "Пополнение баланса",
}

ASYNC_TASK_RESPONSE_EXAMPLE = {
    "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "PENDING",
    "estimated_completion_time": (
        datetime.utcnow() + timedelta(seconds=30)
    ).isoformat(),
}
