from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from app.database.db_config import Base


Base = declarative_base()

class User(Base):
    __tablename__ = 'User'
    
    user_Id = Column(BigInteger, primary_key=True)
    user_role = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(Text, nullable=False)
    isEmailVerified = Column(Boolean, nullable=False)
    gender = Column(Text, nullable=False)
    photoURL = Column(Text, nullable=False)
    emailsTest = Column(String(255), nullable=False)
    cuntry = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    zip_cod = Column(BigInteger, nullable=False)
    credits = Column(Numeric(8, 2), nullable=False)
    is_paid = Column(Boolean, nullable=False)
    status = Column(Boolean, nullable=False)
    createdAt = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=False), nullable=False)
    deleted_by = Column(DateTime(timezone=False), nullable=False)
