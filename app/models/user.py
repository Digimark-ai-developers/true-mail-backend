from sqlalchemy import Column, BigInteger, String, Boolean, Integer, DateTime
from app.database.db_config import Base

class User(Base):
    __tablename__ = 'User'
    
    user_Id = Column(String, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    address = Column(String, nullable=False)  # Using String instead of Text
    city = Column(String, nullable=False)    # Using String instead of Text
    isEmailVerified = Column(Boolean, nullable=False)
    gender = Column(String, nullable=False)  # Using String instead of Text
    photoURL = Column(String, nullable=False) # Using String instead of Text
    creditBalance = Column(Integer, nullable=False)
    stripeCustomerId = Column(String(255), nullable=False)
    emailsTest = Column(String(255), nullable=False)
    cuntry = Column(String(255), nullable=False)  # Note: Typo (likely 'country')
    state = Column(String(255), nullable=False)
    zip_cod = Column(BigInteger, nullable=False)   # Note: Typo (likely 'zip_code')
    createdAt = Column(DateTime(timezone=False), nullable=False)
    updated_at = Column(DateTime(timezone=False), nullable=False)
    deleted_at = Column(DateTime(timezone=False), nullable=False)
    deleted_by = Column(DateTime(timezone=False), nullable=False)