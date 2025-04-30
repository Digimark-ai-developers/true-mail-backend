from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from app.database.db_config import Base


class SubscriptionsStripe(Base):
    __tablename__ = 'Subscriptions Stripe'
    
    subscription_Id = Column(BigInteger, primary_key=True)
    userId = Column(Integer, ForeignKey('User.user_Id'), nullable=False)
    stripeSubscriptionId = Column(Integer, nullable=False)
    stripeCustomerId = Column(Integer, nullable=False)
    status = Column(Boolean, nullable=False)
    current_period_start = Column(DateTime(timezone=False), nullable=False)
    current_period_end = Column(DateTime(timezone=False), nullable=False)
    cancel_at = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=False), nullable=False)
    credits_plan = Column(Integer, nullable=False)
