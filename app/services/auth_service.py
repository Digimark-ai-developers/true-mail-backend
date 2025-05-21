# app/services/auth_service.py
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from firebase_admin import auth as firebase_auth
from firebase_admin._auth_utils import UserNotFoundError  # Import this
from sqlalchemy.orm import Session

from app.models.credits import Credit
from app.models.user import User
from app.schemas.auth import UserRegisterRequest
from app.utils.email_service import send_email_with_link
from app.utils.firebase import verify_firebase_token


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
                photo_url=user_data.photoURL,
            )

            # Generate email verification link and send email
            link = firebase_auth.generate_email_verification_link(user_data.email)
            send_email_with_link(user_data.email, link)

            # Save user to local DB
            new_user = User(
                user_id=firebase_user.uid,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                address=user_data.address,
                city=user_data.city,
                gender=user_data.gender,
                photo_url=user_data.photoURL,
                country=user_data.country,
                state=user_data.state,
                zip_code=str(user_data.zip_code),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                deleted_at=None,
                deleted_by=None,
            )
            credit_entry = Credit(
                user_id=firebase_user.uid,
                is_paid=False,
                total_credits=100,
                remaining_credits=100,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=730),
            )
            credit_entry = Credit(
                user_id=firebase_user.uid,
                is_paid=False,
                total_credits=100,  # add free credits to the use
                remaining_credits=100,  # and remaining credits of uesr
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365),  # 1 years
            )

            self.db.add(credit_entry)

            self.db.add(credit_entry)
            self.db.add(new_user)
            self.db.commit()

            return True  # or return any data you want

        except Exception as e:
            self.db.rollback()
            print(e)
            raise e  # just re-raise the exception

    def login_user(self, id_token: str) -> User:
        try:
            user_info = verify_firebase_token(id_token)
            uid = user_info["uid"]

            # Fetch Firebase user details
            firebase_user = firebase_auth.get_user(uid)
            if not firebase_user.email_verified:
                raise HTTPException(
                    status_code=403,
                    detail="Email not verified. Please verify your email first.",
                )

            # Fetch user from local DB
            user = self.db.query(User).filter(User.user_id == uid).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found. Please register first.")

            return user

        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

    def send_password_reset_email(self, email: str):
        try:
            # Optional: check if user exists
            firebase_auth.get_user_by_email(email)

            reset_link = firebase_auth.generate_password_reset_link(email)
            send_email_with_link(email, reset_link)

            return True  # or any data you want to return

        except UserNotFoundError:
            raise HTTPException(status_code=404, detail="Email not found in Firebase Authentication.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to send password reset email: {str(e)}")

    def change_password(self, uid: str, new_password: str):
        try:
            firebase_auth.update_user(uid, password=new_password)
            return {"message": "Password updated successfully."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")
