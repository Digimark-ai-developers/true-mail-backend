# app/schemas/user.py
from typing import Optional

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


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None


class UserProfileRead(BaseModel):
    user_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    country: Optional[str]
    gender: Optional[str]
    photo_url: Optional[str]

    class Config:
        orm_mode = True
