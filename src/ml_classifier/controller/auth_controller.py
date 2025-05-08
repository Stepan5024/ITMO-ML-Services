# src/ml_classifier/controller/auth_controller.py
"""Authentication API controllers."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.security.jwt import create_access_token
from ml_classifier.infrastructure.web.auth_middleware import (
    get_current_active_user,
)
from ml_classifier.models.auth import (
    ChangePasswordRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from ml_classifier.services.user_use_cases import UserUseCase, get_user_use_case

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate, user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """
    Register a new user.

    Args:
        user_data: User registration data
        user_use_case: User use case dependency

    Returns:
        UserResponse: Created user data

    Raises:
        HTTPException: If registration fails
    """
    success, message, user = await user_use_case.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )

    if not success:
        if "already registered" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        elif "password" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        balance=float(user.balance),
        is_active=user.is_active,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_use_case: UserUseCase = Depends(get_user_use_case),
):
    """
    Authenticate user and issue JWT token.

    Args:
        form_data: OAuth2 form with username (email) and password
        user_use_case: User use case dependency

    Returns:
        TokenResponse: JWT access token

    Raises:
        HTTPException: If authentication fails
    """
    user = await user_use_case.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.id,
        email=user.email,
        is_admin=user.is_admin,
    )

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get information about the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        balance=float(current_user.balance),
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    user_use_case: UserUseCase = Depends(get_user_use_case),
):
    """
    Change the user's password.

    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        user_use_case: User use case dependency

    Returns:
        dict: Success message

    Raises:
        HTTPException: If password change fails
    """
    success, message = await user_use_case.change_password(
        current_user.id,
        password_data.current_password,
        password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {"message": "Password updated successfully"}
