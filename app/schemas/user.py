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
    address: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    model_config = {"from_attributes": True}  # <- this replaces orm_mode = True in Pydantic v2


class UserProfileUpdateWrapper(BaseModel):
    message: str
    status_code: int
    data: UserProfileUpdate


class UserProfileRead(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    model_config = {"from_attributes": True}  # <- this replaces orm_mode = True in Pydantic v2


class UserProfileReadWrapper(BaseModel):
    message: str
    status_code: int
    data: UserProfileRead
