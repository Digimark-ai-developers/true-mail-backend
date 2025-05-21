from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database.db_config import Base


class Credit(Base):
    __tablename__ = "credits"

    credit_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.user_id"), nullable=False, unique=True)
    is_paid = Column(Boolean, default=False)
    total_credits = Column(Integer)
    remaining_credits = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    user = relationship("User", back_populates="credit")


class CreditUsage(Base):
    __tablename__ = "credit_usage"

    usage_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.user_id"), nullable=False)
    email_or_file_id = Column(BigInteger)
    quantity_used = Column(Integer)
    credits_used = Column(DECIMAL(8, 2))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_usage")


class CreditHistory(Base):
    __tablename__ = "credit_history"

    purchase_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.user_id"), nullable=False)
    credits_purchased = Column(DECIMAL(8, 2))
    amount = Column(Float)
    purchased_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_history")
