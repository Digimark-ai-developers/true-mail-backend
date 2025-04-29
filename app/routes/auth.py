# app/routes/auth.py
from fastapi import APIRouter, Depends, Request
from app.models.user import User
from app.database.db_config import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.user import UserResponse
from app.database.db_config import get_db
from app.middlewares.firebase_middleware import verify_firebase_token
import datetime

router = APIRouter()


@router.post("/auth/firebase-login", response_model=UserResponse)
async def firebase_login(request: Request, db: Session = Depends(get_db)):
    await verify_firebase_token(request)
    firebase_user = request.state.firebase_user

    existing_user = db.query(User).filter(User.email == firebase_user["email"]).first()

    if existing_user:
        return existing_user

    # Create new local user with Firebase data
    new_user = User(
        email=firebase_user["mhussainprog@gmail.com"],
        first_name=firebase_user.get("name", ""),
        last_name="",
        photoURL=firebase_user.get("picture", ""),
        isEmailVerified=firebase_user.get("email_verified", False),
        creditBalance=50,  # Give free credits to new users
        stripeCustomerId="",
        emailsTest="",
        cuntry="",
        city="",
        address="",
        state="",
        zip_cod=0,
        createdAt=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
