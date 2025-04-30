from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class SubscriptionStripeBase(BaseModel):
    userId: int
    stripeSubscriptionId: int
    stripeCustomerId: int
    status: bool
    current_period_start: datetime
    current_period_end: datetime
    cancel_at: datetime
    ended_at: datetime
    credits_plan: int

class SubscriptionStripeCreate(SubscriptionStripeBase):
    pass

class SubscriptionStripeUpdate(BaseModel):
    userId: Optional[int] = None
    stripeSubscriptionId: Optional[int] = None
    stripeCustomerId: Optional[int] = None
    status: Optional[bool] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    credits_plan: Optional[int] = None

class SubscriptionStripe(SubscriptionStripeBase):
    subscription_Id: int
    created_at: datetime
    
    class Config:
        orm_mode = True
