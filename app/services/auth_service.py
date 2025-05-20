# app/services/auth_service.py
from firebase_admin import auth
from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin._auth_utils import UserNotFoundError  # Import this
from sqlalchemy.orm import Session
import requests
from app.models.credits import Credit
from app.models.user import User
from app.schemas.auth import UserRegisterRequest
from app.utils.email_service import send_email_with_link
from app.utils.firebase import verify_firebase_token
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
load_dotenv()



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

    def login_with_email_password(self, email: str, password: str) -> User:
        api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        data = response.json()
        uid = data["localId"]
        id_token = data["idToken"]

        return id_token

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

    def delete_firebase_user(self, uid: str, email: str):
        try:
            auth.delete_user(uid)
            return {
                "message": f"User with email '{email}' deleted successfully from Firebase.",
                "status": status.HTTP_200_OK,
            }
        except auth.UserNotFoundError:
            raise HTTPException(status_code=404, detail="User not found in Firebase.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")
