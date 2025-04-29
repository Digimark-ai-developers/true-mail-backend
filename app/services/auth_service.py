from app.schemas.auth import UserRegisterRequest, UserLoginRequest
from app.database.db_config import SessionLocal
from app.models.user import User
# from app.utils.firebase import create_firebase_user, verify_firebase_user
from app.utils.jwt import create_access_token
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from firebase_admin import auth
from app.utils.email_service import send_email_with_link
import firebase_admin
# Just import the module to trigger initialization
import app.utils.firebase

# from app.utils.otp import generate_otp  # For OTP generation if you want


def register_user_service(user):
    try:
        print("dataXXXX",user)
        # Create user in Firebase Auth
        user_record = auth.create_user(
            email=user.email,
            email_verified=False,
            password=user.password,
            display_name=f"{user.first_name} {user.last_name}",
            photo_url=user.photoURL,
            disabled=False,
        )

        # Send Firebase email verification
        link = auth.generate_email_verification_link(user.email)
        send_email_with_link(user.email, link)

                
        return {
            "message": "User created successfully. Please check your email to verify.",
            "verification_link": link
        }
    except Exception as e:
        return {"error": str(e)}

def send_verification_email(email):
    """ Send email verification link to the user's email. """
    user = auth.get_user_by_email(email)
    link = auth.generate_email_verification_link(user.email)
    
    # You can use a service like SendGrid, SMTP, or Firebase's own email provider to send the email
    send_email_with_link(email, link)

def login_user_service(email: str, password: str):
    try:
        # Use Firebase Auth to sign in the user
        # Firebase doesn't directly support login with password like local DB, so we will verify the email and create a token for authentication.
        user = auth.get_user_by_email(email)

        # If user exists, return user information and token
        # Firebase uses JWT to generate a session token instead of password validation directly
        token = auth.create_custom_token(user.uid)

        return {"message": "User logged in successfully", "token": token.decode("utf-8")}
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

