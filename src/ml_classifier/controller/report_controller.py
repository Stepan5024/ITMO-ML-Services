"""Контроллер для API отчетов."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.tasks.report_tasks import (
    generate_transaction_report,
    generate_usage_report,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ReportRequest(BaseModel):
    """Модель запроса для генерации отчета."""

    start_date: date
    end_date: date
    format: str = "json"
    async_execution: bool = True


class ReportResponse(BaseModel):
    """Модель ответа для запроса отчета."""

    task_id: Optional[str] = None
    message: str
    status: str


@router.post("/transactions", response_model=ReportResponse)
async def request_transaction_report(
    report_request: ReportRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Запрашивает генерацию отчета о транзакциях пользователя.

    Если async_execution = True, отчет будет сгенерирован асинхронно,
    и результат можно будет получить по ID задачи.
    """
    try:
        task = generate_transaction_report.delay(
            user_id=str(current_user.id),
            start_date=report_request.start_date.isoformat(),
            end_date=report_request.end_date.isoformat(),
            report_format=report_request.format,
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": "Transaction report generation started",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error requesting transaction report: {str(e)}",
        )


@router.post("/usage", response_model=ReportResponse)
async def request_usage_report(
    report_request: ReportRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Запрашивает генерацию отчета об использовании моделей.

    Если async_execution = True, отчет будет сгенерирован асинхронно,
    и результат можно будет получить по ID задачи.
    """
    try:
        task = generate_usage_report.delay(
            user_id=str(current_user.id),
            start_date=report_request.start_date.isoformat(),
            end_date=report_request.end_date.isoformat(),
            report_format=report_request.format,
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": "Usage report generation started",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error requesting usage report: {str(e)}",
        )
