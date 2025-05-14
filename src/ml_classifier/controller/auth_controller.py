# src/ml_classifier/controller/auth_controller.py
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

from loguru import logger

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate, user_use_case: UserUseCase = Depends(get_user_use_case)
):
    """
    Register a new user.
    """
    logger.info(f"Попытка регистрации пользователя: {user_data.email}")
    try:
        success, message, user = await user_use_case.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )

        if not success:
            logger.warning(f"Регистрация не удалась для {user_data.email}: {message}")
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

        logger.success(f"Пользователь успешно зарегистрирован: {user.email}")
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            balance=float(user.balance),
            is_active=user.is_active,
            is_admin=user.is_admin,
        )
    except Exception as e:
        logger.exception(f"Ошибка при регистрации пользователя: {str(e)}")
        raise


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_use_case: UserUseCase = Depends(get_user_use_case),
):
    """
    Authenticate user and issue JWT token.
    """
    logger.info(f"Попытка входа пользователя: {form_data.username}")
    try:
        user = await user_use_case.authenticate_user(
            form_data.username, form_data.password
        )
        if not user:
            logger.warning("Неверный email или пароль")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Пользователь деактивирован: {user.email}")
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

        logger.success(f"Пользователь успешно вошел: {user.email}")
        return TokenResponse(access_token=access_token)
    except Exception as e:
        logger.exception(f"Ошибка при входе пользователя: {str(e)}")
        raise


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get information about the currently authenticated user.
    """
    logger.info(f"Получение информации о текущем пользователе: {current_user.email}")
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
    """
    logger.info(f"Попытка смены пароля для пользователя: {current_user.email}")
    try:
        success, message = await user_use_case.change_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password,
        )

        if not success:
            logger.warning(
                f"Ошибка смены пароля для пользователя {current_user.email}: {message}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

        logger.success(
            f"Пароль успешно обновлен для пользователя: {current_user.email}"
        )
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.exception(f"Ошибка при смене пароля: {str(e)}")
        raise
