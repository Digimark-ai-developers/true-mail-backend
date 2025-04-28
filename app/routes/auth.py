from fastapi import APIRouter, Depends, HTTPException, Request
import requests  # Import the correct requests library
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from dotenv import load_dotenv
import os
router = APIRouter(prefix="/auth", tags=["Auth"])



load_dotenv()


