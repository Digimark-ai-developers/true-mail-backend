from fastapi import APIRouter, Depends, HTTPException, Request
import requests  # Import the correct requests library
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from app.services.firebase_auth_service import verify_firebase_token
import os
router = APIRouter(prefix="/auth", tags=["Auth"])



load_dotenv()





router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/user")
def get_user_info(user_data: dict = Depends(verify_firebase_token)):
    """Simple protected route: returns user info from Firebase token."""
    return {
        "user_id": user_data.get("uid"),
        "email": user_data.get("email"),
        "message": "User authenticated successfully"
    }

