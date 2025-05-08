from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.db_config import get_db

# from app.schemas.user import UserInfo
from app.schemas.auth import UserRegisterRequest, UserID, UserInfo
from app.services.auth_service import AuthService
from app.utils.jwt_handler import create_jwt_token, get_current_user
from fastapi import Body
from app.schemas.auth import ChangePasswordRequest


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserInfo)
async def get_logged_in_user(user: UserID = Depends(get_current_user)):
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register_user(user_data)


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
        "status_code": 200,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.send_password_reset_email(email)


@router.post("/change-password")
async def change_password(
    db: Session = Depends(get_db),
    payload: ChangePasswordRequest = Body(...),
    current_user=Depends(get_current_user),
):
    auth_service = AuthService(db)

    return auth_service.change_password(current_user.user_Id, payload.new_password)
