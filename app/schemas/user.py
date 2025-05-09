# app/schemas/user.py
from typing import Optional
from pydantic import BaseModel, EmailStr

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone_number: Optional[str] = None


class UserResponse(BaseModel):
    id: str  # The encrypted ID sent to the client as a string
    username: str
    email: str
    phone_number: Optional[str]
    profile_picture_url: Optional[str]
    is_verified: bool


class UserInfo(BaseModel):
    user_id: str
