from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from app.database.db_config import Base


class TestEmails(Base):
    __tablename__ = 'test_emails'
    
    user_id = Column(BigInteger, primary_key=True)
    file_name = Column(String(255), nullable=False)
    user_tested_email = Column(Text, ForeignKey('User.user_Id'), nullable=False)
    is_valid_email = Column(Integer, nullable=False)
    #invalid_email = Column(Integer, nullable=False)
    duplicate_email = Column(Integer, nullable=False)
    email_status = Column(Text, nullable=False)
    deliverable = Column(Text, nullable=False)
    total = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())