from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CreditBalanceResponse(BaseModel):
    credit_id: int
    user_id: str
    is_paid: bool
    total_credits: int
    remaining_credits: int
    # updated_at: Optional[datetime]

    model_config = {"from_attributes": True}  # <- this replaces orm_mode = True in Pydantic v2


class CreditBalanceResponseWrapper(BaseModel):
    message: str
    status: int
    data: CreditBalanceResponse


class CreditUsageResponse(BaseModel):
    usage_id: int
    user_id: str
    email_or_file_id: int
    credits_used: int
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}  # <- this replaces orm_mode = True in Pydantic v2


class CreditUsageResponseWrapper(BaseModel):
    message: str
    status: int
    data: List[CreditUsageResponse]


class CreditHistoryResponse(BaseModel):
    purchase_id: int
    user_id: str
    credits_purchased: int
    amount: float

    model_config = {"from_attributes": True}  # <- this replaces orm_mode = True in Pydantic v2


class CreditHistoryResponseWrapper(BaseModel):
    message: str
    status: int
    data: List[CreditHistoryResponse]
