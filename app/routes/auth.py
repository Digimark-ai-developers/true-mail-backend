import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException, Body
from sqlalchemy.orm import Session
from app.core import security
from app.dependencies.auth import get_current_user, UserInfo
from app.models.user import User
from app.models.otp import OTP
from app.schemas import auth as schema
from app.db.session import SessionLocal
from app.utils.mailer import send_verification_email
from app.utils.response import success_response, error_response
from app.services.otp import generate_otp, store_otp, send_otp_email

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
def forgot_password(
    request: schema.ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Annotated[Session, Depends(get_db)]
):
    # otp = 123456  # simulate OTP
    hashed_password = security.get_password_hash(request.new_password)
    code = generate_otp()
    store_otp(db, request.email, hashed_password, code)

    background_tasks.add_task(send_otp_email, request.email, code)

    return success_response(message="OTP sent to your email.", status_code=status.HTTP_200_OK, data=None)

@router.post("/change_password")
async def change_password(
    db: Session = Depends(get_db),
    payload: schema.ChangePasswordRequest = Body(...),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    Change the password for the currently authenticated user.

    Args:

        payload (ChangePasswordRequest): New password field (min length 6).
        current_user (UserID): The authenticated user.

    Returns:

        dict: Success message and HTTP 200 status code.

    Raises:

        HTTPException: 404 if user is not found or password change fails.

    """
    current_password = security.get_password_hash(payload.old_password)
    user = db.query(User).filter(User.id == current_user.user_id, User.password == current_password).first()
    if not user:
        return error_response(message="Invalid user password.", status_code=status.HTTP_404_NOT_FOUND, data=None)
    
    new_passowrd = security.get_password_hash(payload.new_password)
    user.password = new_passowrd
    db.commit()
    db.refresh(user)
    return success_response(
        message= "Password changed successfully.",
        status_code= status.HTTP_200_OK,
        data=None
    )

@router.post("/verify-otp")
def verify_otp(request: schema.OTPRequest, db: Session = Depends(get_db)):
    try:
        otp_entry = db.query(OTP).filter_by(code=request.otp).first()

        if not otp_entry:
            return error_response(message="OTP not found.", status_code=404, data=None)

        if otp_entry.is_expired():
            db.delete(otp_entry)
            db.commit()
            return error_response(message="OTP expired", status_code=404, data=None)

        if otp_entry.code != request.otp:
            return error_response(message="Invalid OTP.", status_code=404, data=None)

        user = db.query(User).filter(User.email == otp_entry.email).first()
        if not user:
            return error_response(message="User not found.", status_code=404, data=None)
        
        user.password = otp_entry.password
        # Optionally delete OTP after success
        db.delete(otp_entry)
        db.commit()
        db.refresh(user)
        return success_response(
            message="OTP Verified, Your Password Has Been Changed Successfully. You may now login.",
            data=None,
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        # Let FastAPI handle HTTPException as normal
        raise
    except Exception as e:
        return error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
