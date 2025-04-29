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
    stripeCustomerId: str
    emailsTest: str
    country: str
    state: str
    zip_code: int

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    

    class Config:
        from_attributes = True
