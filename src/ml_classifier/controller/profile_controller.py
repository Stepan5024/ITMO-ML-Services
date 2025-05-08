# src/ml_classifier/controller/profile_controller.py
"""User profile API controller."""
from fastapi import APIRouter, Depends, HTTPException, status

from ml_classifier.domain.entities.user import User
from ml_classifier.infrastructure.web.auth_middleware import get_current_active_user
from ml_classifier.models.profile import ProfileResponse, ProfileUpdate
from ml_classifier.services.user_use_cases import UserUseCase, get_user_use_case

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get the profile of the currently authenticated user.

    Args:
        current_user: Current authenticated user

    Returns:
        ProfileResponse: User profile data
    """
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        balance=float(current_user.balance),
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    user_use_case: UserUseCase = Depends(get_user_use_case),
):
    """
    Update the profile of the currently authenticated user.

    Args:
        profile_update: Profile data to update
        current_user: Current authenticated user
        user_use_case: User use case dependency

    Returns:
        ProfileResponse: Updated user profile data
    """
    success, message, updated_user = await user_use_case.update_user(
        current_user.id, full_name=profile_update.full_name
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return ProfileResponse(
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        balance=float(updated_user.balance),
        is_active=updated_user.is_active,
        is_admin=updated_user.is_admin,
    )
