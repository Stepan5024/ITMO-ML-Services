"""Prediction API controller for machine learning models."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from ml_classifier.domain.entities.user import User
from ml_classifier.domain.repositories.ml_model_repository import MLModelRepository

from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.ml_model_repository import (
    SQLAlchemyMLModelRepository,
)
from ml_classifier.infrastructure.db.repositories.ml_model_version_repository import (
    SQLAlchemyMLModelVersionRepository,
)
from ml_classifier.infrastructure.db.repositories.task_repository import (
    SQLAlchemyTaskRepository,
)
from ml_classifier.infrastructure.db.repositories.transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from ml_classifier.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from ml_classifier.infrastructure.ml.model_loader import ModelLoader, ModelNotFoundError
from ml_classifier.infrastructure.ml.prediction_service import (
    InsufficientBalanceError,
    PredictionError,
    PredictionService,
)
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user

router = APIRouter(prefix="/api/v1", tags=["predictions"])


class TextInput(BaseModel):
    """Model for text input data."""

    text: str = Field(..., description="Text to analyze")


class BatchTextInput(BaseModel):
    """Model for batch text input data."""

    items: List[TextInput] = Field(
        ..., min_items=1, max_items=100, description="Text items to analyze"
    )


class PredictionResponse(BaseModel):
    """Model for prediction response."""

    prediction: str = Field(..., description="Prediction result")
    confidence: Optional[float] = Field(None, description="Confidence score")
    categories: Optional[List[str]] = Field(None, description="Detected categories")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class BatchPredictionResponse(BaseModel):
    """Model for batch prediction response."""

    results: List[PredictionResponse] = Field(
        ..., description="List of prediction results"
    )
    execution_time_ms: int = Field(
        ..., description="Total execution time in milliseconds"
    )


class ModelInfo(BaseModel):
    """Model information."""

    id: UUID = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    description: Optional[str] = Field(None, description="Model description")
    model_type: str = Field(..., description="Model type")
    algorithm: str = Field(..., description="Algorithm used")
    price_per_call: float = Field(..., description="Price per prediction call")
    is_active: bool = Field(..., description="Whether the model is active")


class ModelListResponse(BaseModel):
    """Response model for model listing."""

    items: List[ModelInfo] = Field(..., description="List of available models")
    total: int = Field(..., description="Total number of models")


async def get_prediction_service(session=Depends(get_db)):
    """Get prediction service with dependencies."""
    model_repo = SQLAlchemyMLModelRepository(session)
    version_repo = SQLAlchemyMLModelVersionRepository(session)
    user_repo = SQLAlchemyUserRepository(session)
    task_repo = SQLAlchemyTaskRepository(session)
    transaction_repo = SQLAlchemyTransactionRepository(session)

    model_loader = ModelLoader(
        model_repository=model_repo,
        model_version_repository=version_repo,
        model_storage_path="models",
    )

    return PredictionService(
        model_loader=model_loader,
        model_repository=model_repo,
        user_repository=user_repo,
        task_repository=task_repo,
        transaction_repository=transaction_repo,
    )


async def get_model_repository(session=Depends(get_db)):
    """Get model repository with dependencies."""
    return SQLAlchemyMLModelRepository(session)


@router.post("/predict/{model_id}", response_model=PredictionResponse)
async def predict(
    model_id: UUID = Path(..., description="ID of the model to use"),
    input_data: TextInput = ...,
    version_id: Optional[UUID] = Query(
        None, description="Optional specific version ID"
    ),
    current_user: User = Depends(get_current_active_user),
    prediction_service: PredictionService = Depends(get_prediction_service),
    model_repository: MLModelRepository = Depends(get_model_repository),
):
    """
    Make a prediction using the specified model.

    This endpoint charges the user based on the model's price_per_call.
    """
    logger.info(f"Received request for model_id: {model_id}")

    # Verify that the model exists in the database
    model = await model_repository.get_by_id(model_id)
    if not model:
        logger.error(f"Model with ID {model_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    # Check if the model is active
    if not model.is_active:
        logger.error(f"Model with ID {model_id} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with ID {model_id} is not active",
        )

    try:
        result = await prediction_service.predict(
            user_id=current_user.id,
            model_id=model_id,
            data={"text": input_data.text},
            version_id=version_id,
            sandbox=False,
        )
        return result

    except ModelNotFoundError:
        logger.error(f"Model with ID {model_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    except InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    except PredictionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/batch-predict/{model_id}", response_model=BatchPredictionResponse)
async def batch_predict(
    model_id: UUID = Path(..., description="ID of the model to use"),
    input_data: BatchTextInput = ...,
    version_id: Optional[UUID] = Query(
        None, description="Optional specific version ID"
    ),
    current_user: User = Depends(get_current_active_user),
    prediction_service: PredictionService = Depends(get_prediction_service),
    model_repository: MLModelRepository = Depends(get_model_repository),
):
    """
    Make batch predictions using the specified model.

    This endpoint charges the user based on the model's price_per_call multiplied by the batch size.
    """
    # Verify that the model exists in the database
    model = await model_repository.get_by_id(model_id)
    if not model:
        logger.error(f"Model with ID {model_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    # Check if the model is active
    if not model.is_active:
        logger.error(f"Model with ID {model_id} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with ID {model_id} is not active",
        )

    try:
        data_list = [{"text": item.text} for item in input_data.items]

        result = await prediction_service.batch_predict(
            user_id=current_user.id,
            model_id=model_id,
            data_list=data_list,
            version_id=version_id,
            sandbox=False,
        )
        return result

    except ModelNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    except InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    except PredictionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/sandbox/predict/{model_id}", response_model=PredictionResponse)
async def sandbox_predict(
    model_id: UUID = Path(..., description="ID of the model to use"),
    input_data: TextInput = ...,
    version_id: Optional[UUID] = Query(
        None, description="Optional specific version ID"
    ),
    current_user: User = Depends(get_current_active_user),
    prediction_service: PredictionService = Depends(get_prediction_service),
    model_repository: MLModelRepository = Depends(get_model_repository),
):
    """
    Make a test prediction using the specified model.

    This sandbox endpoint does not charge the user.
    """
    # Verify that the model exists in the database
    model = await model_repository.get_by_id(model_id)
    if not model:
        logger.error(f"Model with ID {model_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    try:
        result = await prediction_service.predict(
            user_id=current_user.id,
            model_id=model_id,
            data={"text": input_data.text},
            version_id=version_id,
            sandbox=True,
        )
        return result

    except ModelNotFoundError:
        logger.error(f"Model with ID {model_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    except PredictionError as e:
        logger.error(f"Error during prediction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    search: Optional[str] = Query(None, description="Search in name or description"),
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    current_user: User = Depends(get_current_active_user),
    model_repository: MLModelRepository = Depends(get_model_repository),
):
    """Get a list of available models for prediction."""
    try:
        if search:
            models = await model_repository.search_models(search, model_type=model_type)
            total = len(models)
        else:
            models = await model_repository.get_active_models()
            total = len(models)

        # Check if there are any models to return
        if not models:
            logger.warning("No active models found in the database")
            return ModelListResponse(
                items=[],
                total=0,
            )

        return ModelListResponse(
            items=[
                ModelInfo(
                    id=model.id,
                    name=model.name,
                    description=model.description,
                    model_type=model.model_type,
                    algorithm=model.algorithm,
                    price_per_call=float(model.price_per_call),
                    is_active=model.is_active,
                )
                for model in models
            ],
            total=total,
        )

    except Exception as e:
        logger.error(f"Error retrieving models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving models: {str(e)}",
        )
