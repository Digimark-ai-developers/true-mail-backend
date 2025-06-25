from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core import security
from app.models.user import User
from app.db.session import get_db
from app.schemas import user as schema
from app.dependencies.auth import get_current_user, UserInfo
from app.utils.response import success_response, error_response

router = APIRouter()

@router.get("/me")
async def get_user_profile(
    user_info: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_info.user_id).first()
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    return success_response(
        message="Successfully Executed",
        data={
            "full_name": user.full_name or "",
            "total_credits_assigned": user.total_credits_assigned,
            "remaining_credits": user.remaining_credits,
            "profile_image": user.profile_image or "",
            "email_address": user.email,
            "connected_accounts": user.connected_accounts or []
        },
        status_code=status.HTTP_200_OK
    )

@router.put("/update-profile")
async def update_profile(
    request: schema.UpdateProfileRequest,
    user_info: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_info.user_id).first()
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    if request.email != user.email:
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            return error_response("Email already registered", status_code=status.HTTP_400_BAD_REQUEST)
    user.full_name = request.full_name
    user.email = request.email
    if request.current_password and request.new_password:
        if not security.verify_password(request.current_password, user.password):
            return error_response("Current password is incorrect", status_code=status.HTTP_400_BAD_REQUEST)
        user.password = security.get_password_hash(request.new_password)
    db.commit()
    return success_response(
        message="User Details Updated Successfully",
        data=None,
        status_code=status.HTTP_200_OK
    )
