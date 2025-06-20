from app.core import security
from app.models.user import User
from sqlalchemy.orm import Session
from app.schemas import auth as schema
from app.db.session import SessionLocal
from fastapi import APIRouter, Depends, status
from app.utils.mailer import send_verification_email
from app.utils.response import success_response, error_response
import secrets

router = APIRouter()

fake_otp_db = {}
verification_tokens = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
async def register(request: schema.RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        return error_response("Email already exists", status_code=status.HTTP_400_BAD_REQUEST)
    verification_token = secrets.token_urlsafe(32)
    verification_tokens[request.email] = verification_token
    hashed_password = security.get_password_hash(request.password)
    new_user = User(email=request.email, password=hashed_password, is_active=False)
    db.add(new_user)
    db.commit()
    await send_verification_email(request.email, verification_token)
    return success_response(
        message="Registration successful. Please check your email to verify your account.",
        data=None,
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    email = None
    for stored_email, stored_token in verification_tokens.items():
        if stored_token == token:
            email = stored_email
            break
    if not email:
        return error_response("Invalid verification token", status_code=status.HTTP_400_BAD_REQUEST)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return error_response("User not found", status_code=status.HTTP_404_NOT_FOUND)
    user.is_verified = True
    user.is_active = True
    user.total_credits_assigned = 100
    user.remaining_credits = 100
    db.commit()
    del verification_tokens[email]
    return success_response(
        message="Email verified successfully. You can now login.", data=None, status_code=status.HTTP_200_OK
    )


@router.post("/login")
def login(request: schema.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email, User.is_active == True).first()
    if not user:
        return error_response("Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED)
    if not security.verify_password(request.password, user.password):
        return error_response("Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED)
    access_token = security.create_access_token({"sub": user.email})
    refresh_token = security.create_refresh_token({"sub": user.email})
    return success_response(
        message="Login Successfully",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/refresh")
def refresh_token(request: schema.RefreshTokenRequest):
    payload = security.verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        return error_response("Invalid refresh token", status_code=status.HTTP_401_UNAUTHORIZED)
    access_token = security.create_access_token({"sub": payload["sub"]})
    refresh_token = security.create_refresh_token({"sub": payload["sub"]})
    return success_response(
        message="Successfully Executed",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        status_code=status.HTTP_200_OK,
    )


@router.put("/forgot-password")
def forgot_password(request: schema.ForgotPasswordRequest):
    otp = 123456  # simulate OTP
    fake_otp_db[request.email] = {"otp": otp, "new_password": request.new_password}
    return success_response(message="Password Changed Successfully", data=None, status_code=status.HTTP_200_OK)


@router.post("/verify-otp")
def verify_otp(request: schema.OTPRequest, db: Session = Depends(get_db)):
    for email, record in fake_otp_db.items():
        if record["otp"] == request.otp:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.password = record["new_password"]
                db.commit()
                del fake_otp_db[email]
                return success_response(message="OTP Verified Successfully", data=None, status_code=status.HTTP_200_OK)
    return error_response("Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)
