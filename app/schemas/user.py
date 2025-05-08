from pydantic import BaseModel, EmailStr
from typing import Optional


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
<<<<<<< HEAD
=======

>>>>>>> f34dbfe51f6de61f6019d86d3a4f2ada59e648b2
