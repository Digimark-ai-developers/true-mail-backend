from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    address: str
    city: str
    gender: str
    photoURL: str
    country: str
    state: str
    zip_code: int


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
        orm_mode = True


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
