from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth
from app.utils.firebase_utils import verify_id_token
from app.schemas.auth import UserLogin, UserSignup
from app.services.auth_services import create_user_in_db

router = APIRouter()

@router.post("/signup", response_model=dict)
async def signup(user: UserSignup):
    try:
        # Create user in Firebase Authentication
        firebase_user = auth.create_user(
            email=user.email,
            password=user.password,
            display_name=user.name
        )
        # Save user details in your database
        create_user_in_db(firebase_user.uid, user.email, user.name)
        return {"message": "User created successfully", "uid": firebase_user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=dict)
async def login(user: UserLogin):
    try:
        # Verify Firebase ID token (assuming client sends it)
        decoded_token = verify_id_token(user.id_token)
        return {"message": "Login successful", "user": decoded_token}
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Unauthorized")