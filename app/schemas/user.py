from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from datetime import datetime

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

    # Automatically encrypt user_id before sending the response
    @model_validator(mode="before")
    def encrypt_user_id(cls, values):
        if "id" in values:
            print('VALUES',values)

            # Encrypt the integer ID and convert to string
            values["id"] = encrypt_data(values["id"])  # Assumed encryption returns a string
            print('XXXXX',type(values["id"]))

        return values

    # Decrypt user_id when receiving data from frontend
    @model_validator(mode="after")
    def decrypt_user_id(cls, values):
        if "id" in values:
            # Decrypt the ID (it's a string here, converting back to integer as needed)
            values["id"] = decrypt_data(values["id"])  # Assumed decryption returns an integer
        return values
    
    
    #_____________________
    
    
    
    
# User Schemas
class UserBase(BaseModel):
    user_role: str
    email: EmailStr
    first_name: str
    last_name: str
    address: str
    city: str
    isEmailVerified: bool
    gender: str
    photoURL: str
    emailsTest: str
    cuntry: str
    state: str
    zip_cod: int
    credits: float
    is_paid: bool
    status: bool

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    user_role: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    isEmailVerified: Optional[bool] = None
    gender: Optional[str] = None
    photoURL: Optional[str] = None
    emailsTest: Optional[str] = None
    cuntry: Optional[str] = None
    state: Optional[str] = None
    zip_cod: Optional[int] = None
    credits: Optional[float] = None
    is_paid: Optional[bool] = None
    status: Optional[bool] = None

class User(UserBase):
    user_Id: int
    createdAt: datetime
    updated_at: datetime
    deleted_at: datetime
    deleted_by: datetime
    
    class Config:
        orm_mode = True