## app/services/auth_service.py
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
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

load_dotenv()


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# GOOGLE_CLIENT_ID = "832562555316-5dep9dq8veklnqa3ogom7gba8p76eu5t.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
# GOOGLE_REDIRECT_URI = "https://true-mail-backend.vercel.app/auth/google"
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
# GITHUB_REDIRECT_URI = "https://true-mail-backend.vercel.app/auth/github"
print("Github Redirect URI", GITHUB_REDIRECT_URI, "GITHUB_CLIENT_ID", GITHUB_CLIENT_ID, "github client secret", GITHUB_CLIENT_SECRET)


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
                # photo_url=user_data.photoURL,
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
        fire_base_api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={fire_base_api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        data = response.json()
        id_token = data["idToken"]

        return id_token

    def get_google_oauth_url(self):

        return (
            f"https://accounts.google.com/o/oauth2/auth"
            f"?response_type=code"
            f"&client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_REDIRECT_URI}"
            f"&scope=openid%20profile%20email"
            f"&access_type=offline"
            f"&prompt=consent"
        )

    def exchange_code_for_token(self, code: str):
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            print("❌ Token exchange failed:", response.text)  # <== Add this
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        tokens = response.json()
        id_token = tokens.get("id_token")
        access_token = tokens.get("access_token")

        if not id_token or not access_token:
            raise HTTPException(status_code=400, detail="No id_token or access_token received")

        user_info_response = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})

        if user_info_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        user_info = user_info_response.json()

        return user_info, id_token

    def get_or_create_user(self, user_info: dict, firebase_uid: str = None):
        email = user_info.get("email")
        name = user_info.get("name")

        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                user_id=firebase_uid,  # <-- Store Firebase UID here
                email=email,
                first_name=name,
                # add other fields if needed
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            # Optionally update firebase_uid if changed
            if firebase_uid and user.user_id != firebase_uid:
                user.user_id = firebase_uid
                self.db.commit()

        return user

    def get_user_info(self, access_token: str):
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(user_info_url, headers=headers)
        response.raise_for_status()
        return response.json()

    def login_with_google_user_info(self, id_token: str, provider_id="google.com") -> tuple[str, str]:
        firebase_api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={firebase_api_key}"

        payload = {"postBody": f"id_token={id_token}&providerId={provider_id}", "requestUri": GOOGLE_REDIRECT_URI, "returnSecureToken": True}

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            error_detail = response.json().get("error", {}).get("message", "Unknown error")
            raise HTTPException(status_code=401, detail=f"Google sign-in failed: {error_detail}")

        data = response.json()
        return data["idToken"], data["localId"]  # ✅ return UID too

    def get_github_oauth_url(self):
        return (
            f"https://github.com/login/oauth/authorize" f"?client_id={GITHUB_CLIENT_ID}" f"&redirect_uri={GITHUB_REDIRECT_URI}" f"&scope=user:email"
        )

    def exchange_code_for_github_token(self, code: str):
        print("inside github token exchange")
        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        }

        response = requests.post(token_url, headers=headers, data=data)
        print("GitHub token response:", response.text)

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")

        tokens = response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Fetch user info from GitHub
        user_info_response = requests.get("https://api.github.com/user", headers={"Authorization": f"token {access_token}"})
        if user_info_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")

        user_info = user_info_response.json()

        # Optional: fetch email (separate endpoint if email is not public)
        if not user_info.get("email"):
            emails_response = requests.get("https://api.github.com/user/emails", headers={"Authorization": f"token {access_token}"})
            if emails_response.status_code == 200:
                primary_email = next((email["email"] for email in emails_response.json() if email["primary"]), None)
                user_info["email"] = primary_email

        # GitHub doesn't return an ID token, so you'll use access_token in Firebase login
        return user_info, access_token

    def login_with_github_access_token(self, access_token: str, provider_id="github.com") -> tuple[str, str]:
        firebase_api_key = os.getenv("FIREBASE_API_KEY")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={firebase_api_key}"

        payload = {"postBody": f"access_token={access_token}&providerId={provider_id}", "requestUri": GITHUB_REDIRECT_URI, "returnSecureToken": True}

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            error_detail = response.json().get("error", {}).get("message", "Unknown error")
            raise HTTPException(status_code=401, detail=f"GitHub sign-in failed: {error_detail}")

        data = response.json()
        return data["idToken"], data["localId"]

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
