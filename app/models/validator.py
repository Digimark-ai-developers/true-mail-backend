import uuid
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class FileValidation(Base):
    __tablename__ = "file_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    file_name = Column(String)
    duplicate_email = Column(Integer)  # how much duplicates in a file
    total_valid_emails = Column(Integer)
    status = Column(String)
    deliverable = Column(Integer)
    undeliverable = Column(Integer)
    total = Column(Integer)
    risky = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    soft_delete = Column(Boolean)

    user = relationship("User", back_populates="file_validations")
    single_validations = relationship("SingleValidation", back_populates="file_validation")


class SingleValidation(Base):
    __tablename__ = "single_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    file_id = Column(Integer, ForeignKey("file_validation.id"), nullable=True)
    validated_email = Column(String, index=True)
    score = Column(Float)

    # General
    full_name = Column(String)
    gender = Column(String)
    status = Column(String)  # "deliverable" | "undeliverable" | "risky" | "duplicate"
    reason = Column(String)
    domain = Column(String)

    # Details
    is_free = Column(Boolean)
    has_role = Column(Boolean)
    disposable = Column(Boolean)
    accept_all = Column(Boolean)
    has_tag = Column(Boolean)
    numerical_characters = Column(Integer)
    alphabetical_characters = Column(Integer)
    unicode_symbols = Column(Integer)
    is_mailbox_full = Column(Boolean)
    is_no_reply = Column(Boolean)

    # Checks for status
    is_risky = Column(Boolean)
    is_valid = Column(Boolean)
    is_deliverable = Column(Boolean)

    # Mail server information
    smtp_provider = Column(String)
    mx_record = Column(String)
    implicit_mx_record = Column(String)

    # Usage
    soft_delete = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="single_validations")
    file_validation = relationship("FileValidation", back_populates="single_validations")
