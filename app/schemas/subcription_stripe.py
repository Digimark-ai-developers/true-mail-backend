from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserInfo(BaseModel):
    user_Id: str
    email: EmailStr
    first_name: str
    last_name: str
    photoURL: Optional[str]

    class Config:
        from_attributes = True


class CheckoutSessionRequest(BaseModel):
    success_url: str
    card_price: int
    # user_id: str
    credits: int


class GetInvoices(BaseModel):
    id: int
    amount: int
    number: str
    status: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Required for ORM objects


class GetInvoicesWrapper(BaseModel):
    message: str
    status_code: int
    data: list[GetInvoices]
