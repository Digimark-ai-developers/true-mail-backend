from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import relationship
from app.database.db_config import Base


class BulkEmailStats(Base):
    __tablename__ = "bulk_emails_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    file_name = Column(String(255))
    user_tested_email = Column(Text)
    duplicate_email = Column(Integer)  # how much duplicates in a file i numbers
    total_valid_emails = Column(Integer)
    email_status = Column(Text)
    deliverable = Column(Float)
    is_risky = Column(Boolean)
    total = Column(Integer)
    created_at = Column(DateTime)

    user = relationship("User", backref="bulk_emails_stats")


class TestEmail(Base):
    __tablename__ = "test_email"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    file_id = Column(Integer, ForeignKey("bulk_emails_stats.id"), nullable=True)
    user_tested_email = Column(Text)
    full_name = Column(String(255))
    gender = Column(String)
    status = Column(String)
    reason = Column(String)
    domain = Column(String(255))
    is_free = Column(Boolean)
    is_valid = Column(Boolean)
    is_disposable = Column(Boolean)
    is_deliverable = Column(Boolean)
    has_tag = Column(Boolean)
    alphabetical_characters = Column(Integer)
    is_mailbox_full = Column(Boolean)
    has_role = Column(Boolean)
    is_accept_all = Column(Boolean)
    has_numerical_characters = Column(Integer)
    has_unicode_symbols = Column(Integer)
    has_no_reply = Column(Boolean)
    smtp_provider = Column(String(255))
    mx_record = Column(String(255))
    implicit_mx_record = Column(String(255))
    score = Column(Integer)
    created_at = Column(DateTime)

    user = relationship("User", backref="test_emails")
    bulk_email_stats = relationship("BulkEmailStats", backref="test_emails")
