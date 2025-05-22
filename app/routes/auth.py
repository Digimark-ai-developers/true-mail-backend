from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from app.database.db_config import get_db

# from app.schemas.user import UserInfo
from app.schemas.auth import UserID, UserInfo, UserRegisterRequest
from app.services.auth_service import AuthService
from app.utils.jwt_handler import get_current_user
from fastapi import Body
from app.schemas.auth import ChangePasswordRequest


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserInfo)
async def get_logged_in_user(user: UserID = Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's information.

    Args:

        user (UserID): The authenticated user object retrieved via dependency injection.

    Returns:

        UserInfo: Contains user ID, email, names, and optional profile photo.

    Raises:

        HTTPException: 401 if user is not authenticated.
    """
    print(user.user_Id)
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with the provided credentials and optional profile information.

    Args:
        user_data (UserRegisterRequest): The registration payload including:

            - email (str)
            - password (str)
            - first_name, last_name, address, city, gender, photoURL, country, state, zip_code (optional fields)

    Returns:

        dict: Success message and HTTP status code 201.

    Raises:

        HTTPException: 400 if registration fails due to validation or duplicate email.

    """

    service = AuthService(db)
    try:
        service.register_user(user_data)
        return {
            "message": "User registered successfully. Please verify your email.",
            "status_code": status.HTTP_201_CREATED,
        }
    except Exception as e:
        # you can customize error handling here if needed
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login_user(email: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    """
    Authenticate a user using email and password, returning a Firebase ID token.

    Args:

        email (str): User's email address.
        password (str): User's password.

    Returns:

        dict: Success message, HTTP 200 status code, and Firebase ID token.

    Raises:

        HTTPException: 401 if authentication fails.

    Example:

        {
            "email": "user@example.com",
            "password": "SecurePass123"
        }
    """
    auth_service = AuthService(db)

    firebase_id_token = auth_service.login_with_email_password(email, password)  # ✅ unpack here

    # token = create_jwt_token({"user_Id": user.user_id})  # ✅ user is now the correct object

    return {
        "message": "Login successful",
        "status_code": status.HTTP_200_OK,
        "firebase_id_token": firebase_id_token,  # optional: include if you need it
    }


@router.get("/login_google")
def login_google(db: Session = Depends(get_db)):
    """
    Generate the Google OAuth 2.0 login URL for user authentication.

    Args:

         db (Session): SQLAlchemy session used to access the database.

    Returns:

        dict: Contains the Google OAuth URL to initiate login via frontend.

    """

    auth_service = AuthService(db)

    return {"url": auth_service.get_google_oauth_url()}


@router.get("/google")
def auth_google(code: str, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback, authenticate the user, and redirect to frontend.

    Args:

        code (str): Authorization code returned by Google after user consent.
        db (Session): SQLAlchemy session used to access the database.

    Returns:

        RedirectResponse: Redirects the user to the frontend dashboard with the Firebase token in the query string.

    Raises:

        HTTPException: 400 if token exchange, user info retrieval, or Firebase login fails.
    """

    try:
        auth_service = AuthService(db)

        # Get user info and Google id_token
        user_info, google_id_token = auth_service.exchange_code_for_token(code)

        # Log in with Firebase using Google id_token
        firebase_id_token, firebase_uid = auth_service.login_with_google_user_info(google_id_token)
        auth_service.get_or_create_user(user_info, firebase_uid=firebase_uid)

        # Redirect to frontend with token and user data
        params = urlencode(
            {
                "token": firebase_id_token,
            }
        )
        frontend_redirect = f"http://localhost:5173/home?{params}"
        return RedirectResponse(url=frontend_redirect)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forgot_password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    """
    Send a password reset email to the user.

    Args:

        email (str): Registered email address of the user.

    Returns:

        dict: Success message and HTTP 200 status code.

    Raises:

        HTTPException: 400 if the email is invalid or user does not exist.
    """
    auth_service = AuthService(db)
    try:
        auth_service.send_password_reset_email(email)
        return {
            "message": "Password reset email sent successfully.",
            "status_code": status.HTTP_200_OK,
        }
    except HTTPException as e:
        # re-raise so FastAPI handles HTTPException properly
        raise e
    except Exception as e:
        # catch other errors if you want, or let them propagate
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change_password")
async def change_password(
    db: Session = Depends(get_db),
    payload: ChangePasswordRequest = Body(...),
    current_user=Depends(get_current_user),
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
    auth_service = AuthService(db)
    result = auth_service.change_password(current_user.user_Id, payload.new_password)
    return {
        "message": result["message"],
        "status_code": status.HTTP_200_OK,
    }


@router.delete("/delete", status_code=status.HTTP_200_OK)
def delete_user_account(
    user: UserID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the account of the currently authenticated user.

    Args:

        user (UserID): The authenticated user whose account is to be deleted.

    Returns:

        dict: Result of the deletion from Firebase.

    Raises:

        HTTPException: 400 or 500 if deletion fails.
    """
    service = AuthService(db)
    return service.delete_firebase_user(uid=user.user_Id, email=user.email)
