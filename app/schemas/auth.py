from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None
    photoURL: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class UserRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    first_name: str
    last_name: str
    address: str
    city: str
    gender: str
    photo_url: str
    country: str
    state: str
    zip_code: str

    class Config:
        from_attributes = True


class UserID(BaseModel):
    user_id: str


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, example="NewSecurePass123")


class UserInfo(BaseModel):
    user_Id: str
    email: EmailStr
    first_name: str
    last_name: str
    photoURL: Optional[str]

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
