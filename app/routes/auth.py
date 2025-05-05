from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.schemas.auth import UserRegisterRequest, UserInfo
from app.services.auth_service import AuthService
from app.utils.jwt_handler import create_jwt_token
from fastapi import Body

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register_user(user_data)


@router.post("/login")
def login_user(
    id_token: str = Body(..., embed=True),  # expects {"id_token": "..."}
    db=Depends(get_db)
):
    auth_service = AuthService(db)
    user = auth_service.login_user(id_token)

    token = create_jwt_token({"user_Id": user.user_Id})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.send_password_reset_email(email)