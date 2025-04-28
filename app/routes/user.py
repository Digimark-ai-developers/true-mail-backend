from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db_config import get_db
# from app.services.user_service import UserService
#from app.models.user import User

router = APIRouter()


