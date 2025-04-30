from fastapi import APIRouter, Depends, HTTPException, Request
from firebase_admin import auth as firebase_auth
from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas.user import UserResponse
from app.models.user import User
from app.database.db_config import SessionLocal

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/firebase-login", response_model=UserResponse)
def firebase_login(request: Request, db: Session = Depends(get_db)):
    firebase_user = request.state.user  # Comes from Firebase middleware
    email = firebase_user["email"]
    uid = firebase_user["uid"]

    user = db.query(User).filter_by(email=email).first()
    if not user:
        # Create new user if not found
        user = User(
            user_role="user",  # default role
            email=email,
            first_name="",
            last_name="",
            address="",
            city="",
            is_Email_Verified=firebase_user.get("email_verified", False),
            gender="",
            photo_url=firebase_user.get("picture", ""),
            emails_test="",
            cuntry="",
            state="",
            zip_code=0,
            credits=0.00,
            is_paid=False,
            status=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=datetime.now(),
            deleted_by=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return UserResponse(**user.__dict__)
