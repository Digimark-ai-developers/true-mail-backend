from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str

class ConnectedAccount(BaseModel):
    service_id: int
    service_name: str  # "google" | "microsoft"

class UserProfile(BaseModel):
    full_name: str
    total_credits_assigned: int
    remaining_credits: int
    profile_image: str
    email_address: str
    connected_accounts: List[ConnectedAccount]

class UserProfileResponse(BaseModel):
    message: str
    status: int
    data: UserProfile

class UpdateProfileRequest(BaseModel):
    full_name: str
    email: EmailStr
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class UpdateProfileResponse(BaseModel):
    message: str
    status: int
    data: dict

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class BillingAddress(BaseModel):
    first_name: str
    last_name: str
    address: str
    country: str
    city: str
    state: str
    zip_code: str

class BillingAddressResponse(BaseModel):
    message: str
    status: int
    data: BillingAddress 