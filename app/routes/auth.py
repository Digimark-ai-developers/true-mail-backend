from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db_config import get_db

# from app.schemas.user import UserInfo
from app.schemas.auth import (
    ChangePasswordRequest,
    UserID,
    UserInfo,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService
from app.utils.jwt_handler import create_jwt_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserInfo)
async def get_logged_in_user(user: UserID = Depends(get_current_user)):
    print(user.user_Id)
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):

    service = AuthService(db)
    try:
        service.register_user(user_data)
        return {
            "message": "User registered successfully. Please verify your email.",
            "status_code": status.HTTP_201_CREATED,
        }
    except Exception as e:
        # you can customize error handling here if needed
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login_user(
    id_token: str = Body(..., embed=True),  # expects {"id_token": "..."}
    db=Depends(get_db),
):
    auth_service = AuthService(db)
    user = auth_service.login_user(id_token)

    token = create_jwt_token({"user_Id": user.user_id})

    return {
        "message": "Login successful",
        "status_code": status.HTTP_200_OK,
        "access_token": token,
    }


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        auth_service.send_password_reset_email(email)
        return {
            "message": "Password reset email sent successfully.",
            "status_code": status.HTTP_200_OK,
        }
    except HTTPException as e:
        # re-raise so FastAPI handles HTTPException properly
        raise e
    except Exception as e:
        # catch other errors if you want, or let them propagate
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change-password")
async def change_password(
    db: Session = Depends(get_db),
    payload: ChangePasswordRequest = Body(...),
    current_user=Depends(get_current_user),
):
    auth_service = AuthService(db)
    result = auth_service.change_password(current_user.user_Id, payload.new_password)
    return {
        "message": result["message"],
        "status_code": status.HTTP_200_OK,
    }


@router.delete("/delete", status_code=status.HTTP_200_OK)
def delete_user_account(
    user: UserID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.delete_firebase_user(uid=user.user_Id, email=user.email)
