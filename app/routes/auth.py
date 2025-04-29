from fastapi import APIRouter, Depends, HTTPException
from app.schemas.auth import UserRegisterRequest, UserLoginRequest
from app.services.auth_service import login_user_service, register_user_service
from firebase_admin import auth


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register")
async def register(user: UserRegisterRequest):
    result = register_user_service(user)
    return {"message": "User registered successfully", "user_id": result}

@router.post("/login")
async def login(user: UserLoginRequest):
    token = login_user_service(user.email, user.password)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/verify-email")
def verify_email(email: str):
    try:
        user = auth.get_user_by_email(email)
        if user.email_verified:
            return {"message": "Email is already verified."}
        else:
            return {"message": "Email verification pending."}
    except Exception as e:
        raise HTTPException(status_code=404, detail="User not found")
