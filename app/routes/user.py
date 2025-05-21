from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.schemas.auth import UserID
from app.schemas.user import (
    UserProfileReadWrapper,
    UserProfileUpdate,
    UserProfileUpdateWrapper,
)
from app.services.user_service import fetch_user_profile, update_user_profile
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/user", tags=["User "])


@router.get("/profile", response_model=UserProfileReadWrapper, summary="Get user profile")
def get_user_profile(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = fetch_user_profile(user.user_Id, db)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileReadWrapper(
        message="User profile retrieved successfully", status_code=status.HTTP_200_OK, data=profile
    )


@router.put("/update", response_model=UserProfileUpdateWrapper, summary="Update current user profile")
def update_user_profile_route(
    user_data: UserProfileUpdate,
    user: UserID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = update_user_profile(user.user_Id, user_data, db)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfileUpdateWrapper(
        message="User updated successfully.", status_code=status.HTTP_200_OK, data=updated_user
    )
