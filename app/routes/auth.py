from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.schemas.auth import UserRegisterRequest, UserInfo
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register_user(user_data)


@router.post("/login", response_model=UserInfo, status_code=status.HTTP_200_OK)
def login_user(data: UserRegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.login_user(data.id_token)
    return user