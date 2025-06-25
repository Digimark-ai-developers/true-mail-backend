from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    success_url: str
    card_price: int
    user_id: int
    credits: int


class GetInvoices(BaseModel):
    id: int
    amount: Optional[int]
    number: str
    status: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Required for ORM objects


class GetInvoicesWrapper(BaseModel):
    message: str
    status_code: int
    data: list[GetInvoices]
