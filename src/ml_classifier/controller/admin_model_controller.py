# src/ml_classifier/controller/admin_model_controller.py
"""Admin controller for managing ML models."""
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.db.database import get_db
from ml_classifier.infrastructure.db.repositories.ml_model_repository import (
    SQLAlchemyMLModelRepository,
)
from ml_classifier.infrastructure.db.repositories.ml_model_version_repository import (
    SQLAlchemyMLModelVersionRepository,
)
from ml_classifier.infrastructure.ml.model_storage import ModelStorage
from ml_classifier.infrastructure.web.auth_middleware import get_current_admin_user
from ml_classifier.models.ml_models import (
    ModelCreate,
    ModelResponse,
    ModelListResponse,
    ModelUpdate,
    ModelVersionResponse,
    ModelVersionStatus,
    ModelVersionListResponse,
)

from ml_classifier.services.model_use_cases import ModelUseCase, ModelVersionUseCase

router = APIRouter(prefix="/api/v1/admin", tags=["admin-models"])

# Setup services
model_storage = ModelStorage()


async def get_model_use_case(session=Depends(get_db)):
    """Get model use case with dependencies."""
    model_repo = SQLAlchemyMLModelRepository(session)
    version_repo = SQLAlchemyMLModelVersionRepository(session)
    return ModelUseCase(model_repo, version_repo)


async def get_model_version_use_case(session=Depends(get_db)):
    """Get model version use case with dependencies."""
    model_repo = SQLAlchemyMLModelRepository(session)
    version_repo = SQLAlchemyMLModelVersionRepository(session)
    return ModelVersionUseCase(model_repo, version_repo)


# Model management endpoints
@router.post(
    "/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED
)
async def create_model(
    model_data: ModelCreate,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Create a new ML model.

    Admin-only endpoint for creating a new machine learning model.
    """
    success, message, model = await model_use_case.create_model(model_data.dict())

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        algorithm=model.algorithm,
        input_schema=model.input_schema,
        output_schema=model.output_schema,
        price_per_call=model.price_per_call,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    search: Optional[str] = Query(None, description="Search in name or description"),
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    List ML models with filtering and pagination.

    Admin-only endpoint for listing machine learning models.
    """
    models, total = await model_use_case.list_models(
        skip=(page - 1) * size,
        limit=size,
        search=search,
        model_type=model_type,
        is_active=is_active,
    )

    return ModelListResponse(
        items=[
            ModelResponse(
                id=model.id,
                name=model.name,
                description=model.description,
                model_type=model.model_type,
                algorithm=model.algorithm,
                input_schema=model.input_schema,
                output_schema=model.output_schema,
                price_per_call=model.price_per_call,
                is_active=model.is_active,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Get information about a specific ML model.

    Admin-only endpoint for retrieving model details.
    """
    model = await model_use_case.get_model_by_id(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID {model_id} not found",
        )

    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        algorithm=model.algorithm,
        input_schema=model.input_schema,
        output_schema=model.output_schema,
        price_per_call=model.price_per_call,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.put("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Update an existing ML model.

    Admin-only endpoint for updating model details.
    """
    # Filter out None values
    update_data = {k: v for k, v in model_data.dict().items() if v is not None}

    success, message, updated_model = await model_use_case.update_model(
        model_id, update_data
    )

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ModelResponse(
        id=updated_model.id,
        name=updated_model.name,
        description=updated_model.description,
        model_type=updated_model.model_type,
        algorithm=updated_model.algorithm,
        input_schema=updated_model.input_schema,
        output_schema=updated_model.output_schema,
        price_per_call=updated_model.price_per_call,
        is_active=updated_model.is_active,
        created_at=updated_model.created_at,
        updated_at=updated_model.updated_at,
    )


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Delete an ML model and all its versions.

    Admin-only endpoint for deleting a model.
    """
    success, message = await model_use_case.delete_model(model_id)

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.post("/models/{model_id}/activate", response_model=ModelResponse)
async def activate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Activate an ML model.

    Admin-only endpoint for activating a model.
    """
    success, message, model = await model_use_case.activate_model(model_id)

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        algorithm=model.algorithm,
        input_schema=model.input_schema,
        output_schema=model.output_schema,
        price_per_call=model.price_per_call,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post("/models/{model_id}/deactivate", response_model=ModelResponse)
async def deactivate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    model_use_case: ModelUseCase = Depends(get_model_use_case),
):
    """
    Deactivate an ML model.

    Admin-only endpoint for deactivating a model.
    """
    success, message, model = await model_use_case.deactivate_model(model_id)

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ModelResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        algorithm=model.algorithm,
        input_schema=model.input_schema,
        output_schema=model.output_schema,
        price_per_call=model.price_per_call,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# Model version management endpoints
@router.post(
    "/models/{model_id}/versions",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    model_id: UUID,
    model_file: UploadFile = File(..., description="Model file (.joblib or .pkl)"),
    vectorizer_file: Optional[UploadFile] = File(
        None, description="TF-IDF vectorizer file (.joblib or .pkl)"
    ),
    version: str = Form(...),
    metrics: str = Form("{}"),
    parameters: str = Form("{}"),
    status_value: ModelVersionStatus = Form(ModelVersionStatus.TRAINED),
    current_user: User = Depends(get_current_admin_user),
    version_use_case: ModelVersionUseCase = Depends(get_model_version_use_case),
):
    """
    Upload a new version of an ML model with optional vectorizer.
    """
    import json

    try:
        # Parse JSON strings
        metrics_dict = json.loads(metrics)
        parameters_dict = json.loads(parameters)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON format: {str(e)}",
        )

    version_data = {
        "version": version,
        "metrics": metrics_dict,
        "parameters": parameters_dict,
        "status": status_value,
    }

    try:
        # Pass both files to the use case
        success, message, created_version = await version_use_case.create_version(
            model_id=model_id,
            version_data=version_data,
            model_file=model_file,
            vectorizer_file=vectorizer_file,
            user_id=current_user.id,
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

        return ModelVersionResponse(
            id=created_version.id,
            model_id=created_version.model_id,
            version=created_version.version,
            file_path=created_version.file_path,
            metrics=created_version.metrics,
            parameters=created_version.parameters,
            is_default=created_version.is_default,
            created_by=created_version.created_by,
            file_size=created_version.file_size,
            status=created_version.status,
            created_at=created_version.created_at,
            updated_at=created_version.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/models/{model_id}/versions", response_model=ModelVersionListResponse)
async def list_versions(
    model_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    version_use_case: ModelVersionUseCase = Depends(get_model_version_use_case),
):
    """
    List all versions of an ML model.

    Admin-only endpoint for listing model versions.
    """
    versions = await version_use_case.list_versions(model_id)

    return ModelVersionListResponse(
        items=[
            ModelVersionResponse(
                id=version.id,
                model_id=version.model_id,
                version=version.version,
                file_path=version.file_path,
                metrics=version.metrics,
                parameters=version.parameters,
                is_default=version.is_default,
                created_by=version.created_by,
                file_size=version.file_size,
                status=version.status,
                created_at=version.created_at,
                updated_at=version.updated_at,
            )
            for version in versions
        ],
        total=len(versions),
    )


@router.get("/versions/{version_id}", response_model=ModelVersionResponse)
async def get_version(
    version_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    version_use_case: ModelVersionUseCase = Depends(get_model_version_use_case),
):
    """
    Get information about a specific model version.

    Admin-only endpoint for retrieving version details.
    """
    version = await version_use_case.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version with ID {version_id} not found",
        )

    return ModelVersionResponse(
        id=version.id,
        model_id=version.model_id,
        version=version.version,
        file_path=version.file_path,
        metrics=version.metrics,
        parameters=version.parameters,
        is_default=version.is_default,
        created_by=version.created_by,
        file_size=version.file_size,
        status=version.status,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    version_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    version_use_case: ModelVersionUseCase = Depends(get_model_version_use_case),
):
    """
    Delete a specific model version.

    Admin-only endpoint for deleting a model version.
    """
    success, message = await version_use_case.delete_version(version_id)

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        if "default version" in message.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@router.post("/versions/{version_id}/set-default", response_model=ModelVersionResponse)
async def set_default_version(
    version_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    version_use_case: ModelVersionUseCase = Depends(get_model_version_use_case),
):
    """
    Set a version as the default for its model.

    Admin-only endpoint for setting the default model version.
    """
    success, message, version = await version_use_case.set_default_version(version_id)

    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ModelVersionResponse(
        id=version.id,
        model_id=version.model_id,
        version=version.version,
        file_path=version.file_path,
        metrics=version.metrics,
        parameters=version.parameters,
        is_default=version.is_default,
        created_by=version.created_by,
        file_size=version.file_size,
        status=version.status,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )
