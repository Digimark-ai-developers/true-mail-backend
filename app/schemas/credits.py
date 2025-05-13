"""Credits schemas"""

from datetime import datetime

from pydantic import BaseModel


class CreditUsageBase(BaseModel):
    """Base model for credit usage"""

    user_id: str
    email_or_file_id: int
    quantity_used: int
    credits_used: int
    created_at: datetime
