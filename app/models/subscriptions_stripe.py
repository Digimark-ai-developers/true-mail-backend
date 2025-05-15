from sqlalchemy import DECIMAL, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.db_config import Base


class SubscriptionsStripe(Base):
    __tablename__ = "subscriptions_stripe"

    subscription_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    stripe_subscription_id = Column(String)
    stripe_customer_id = Column(String)
    subscription_plan = Column(String)
    status = Column(Boolean)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at = Column(DateTime)
    created_at = Column(DateTime)
    ended_at = Column(DateTime)

    user = relationship("User", backref="subscriptions_stripe")


class Invoices(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    total = Column(DECIMAL(8, 2))
    amount = Column(DECIMAL)
    number = Column(String)
    tax = Column(DECIMAL(8, 2))
    status = Column(Boolean, default=False)
    card_country = Column(String(255))
    billing_state = Column(String(255))
    billing_zip = Column(String(255))
    billing_country = Column(String(255))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    deleted_at = Column(DateTime)
    deleted_by = Column(DateTime)

    user = relationship("User", backref="invoices")
