from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from fastapi import status

router = APIRouter(prefix="/users", tags=['Users'])

#route for get users 
@router.get("/me", status_code=status.HTTP_200_OK)
def get_user_info( ):
    
    return 

#route for user update
@router.put("/{user_Id}", response_model=UserResponse)
def update_user():
    return

