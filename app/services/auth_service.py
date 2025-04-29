from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserRegisterRequest
from app.utils.firebase import verify_firebase_token
from datetime import datetime
from firebase_admin import auth as firebase_auth

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, user_data: UserRegisterRequest):
        try:
            # Step 1: Create user in Firebase
            firebase_user = firebase_auth.create_user(
                email=user_data.email,
                password=user_data.password,
                display_name=f"{user_data.first_name} {user_data.last_name}",
                photo_url=user_data.photoURL
            )

            # Step 2: Save user to local DB
            new_user = User(
                user_Id=firebase_user.uid,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                address=user_data.address,
                city=user_data.city,
                isEmailVerified=False,
                gender=user_data.gender,
                photoURL=user_data.photoURL,
                creditBalance=user_data.creditBalance,
                stripeCustomerId=user_data.stripeCustomerId,
                emailsTest=user_data.emailsTest,
                cuntry=user_data.country,
                state=user_data.state,
                zip_cod=user_data.zip_code,
                createdAt=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deleted_at=datetime.utcnow(),
                deleted_by=datetime.utcnow()
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            return new_user

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))


    def login_user(self, id_token: str) -> User:
        try:
            user_info = verify_firebase_token(id_token)
            uid = user_info["uid"]

            user = self.db.query(User).filter(User.user_Id == uid).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found. Please register first.")

            return user
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")