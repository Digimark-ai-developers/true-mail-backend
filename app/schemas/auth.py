from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    address: str
    city: str
    gender: str
    photoURL: str
    creditBalance: int
    stripeCustomerId: str
    emailsTest: str
    country: str
    state: str
    zip_code: int


class UserInfo(BaseModel):
    user_Id: str
    email: EmailStr
    first_name: str
    last_name: str
    photoURL: Optional[str]

    class Config:
        from_attributes = True
