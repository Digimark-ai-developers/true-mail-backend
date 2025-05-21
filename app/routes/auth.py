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
    print(user.user_Id)
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegisterRequest, db: Session = Depends(get_db)):
 
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


@router.get("/login/google")
def login_google(db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    print("OAuth URL:", auth_service.get_google_oauth_url())  # ✅ Safe print

    return {"url": auth_service.get_google_oauth_url()}

@router.get("/google")
def auth_google(code: str, db: Session = Depends(get_db)):
    try:
        auth_service = AuthService(db)

        # Get user info and Google id_token
        user_info, google_id_token = auth_service.exchange_code_for_token(code)

        # Log in with Firebase using Google id_token
        firebase_id_token, firebase_uid = auth_service.login_with_google_user_info(google_id_token)
        user = auth_service.get_or_create_user(user_info, firebase_uid=firebase_uid)

        # Redirect to frontend with token and user data
        params = urlencode({
            "token": firebase_id_token,
            "email": user.email,
            "name": user.first_name
        })
        frontend_redirect = f"http://localhost:3000/dashboard?{params}"
        return RedirectResponse(url=frontend_redirect)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.post("/login")
def login_user(email: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    
    firebase_id_token = auth_service.login_with_email_password(email, password)  # ✅ unpack here

    # token = create_jwt_token({"user_Id": user.user_id})  # ✅ user is now the correct object

    return {
        "message": "Login successful",
        "status_code": status.HTTP_200_OK,
        "firebase_id_token": firebase_id_token,  # optional: include if you need it
    }



@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
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


@router.post("/change-password")
async def change_password(
    db: Session = Depends(get_db),
    payload: ChangePasswordRequest = Body(...),
    current_user=Depends(get_current_user),
):
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
    service = AuthService(db)
    return service.delete_firebase_user(uid=user.user_Id, email=user.email)
