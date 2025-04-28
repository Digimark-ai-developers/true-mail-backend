from datetime import datetime, timedelta
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

class AuthService:
    def __init__(self, db: Session):
        self.db = db

