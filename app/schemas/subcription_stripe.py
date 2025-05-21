from typing import Optional

from pydantic import BaseModel, EmailStr


class UserInfo(BaseModel):
    user_Id: str
    email: EmailStr
    first_name: str
    last_name: str
    photoURL: Optional[str]

    class Config:
        from_attributes = True


class CheckoutSessionRequest(BaseModel):
    card_title: str
    card_price: int
    user_id: str
    credits: int
