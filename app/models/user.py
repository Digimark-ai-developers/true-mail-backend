from sqlalchemy import Boolean, Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # Store hashed password
    full_name = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # Credits
    total_credits_assigned = Column(Integer, default=0)
    remaining_credits = Column(Integer, default=0)
    
    # Connected accounts
    connected_accounts = Column(JSON, default=list)
    
    # Billing address
    billing_first_name = Column(String, nullable=True)
    billing_last_name = Column(String, nullable=True)
    billing_address = Column(String, nullable=True)
    billing_country = Column(String, nullable=True)
    billing_city = Column(String, nullable=True)
    billing_state = Column(String, nullable=True)
    billing_zip_code = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Add relationships
    file_validations = relationship("FileValidation", back_populates="user")
    single_validations = relationship("SingleValidation", back_populates="user")