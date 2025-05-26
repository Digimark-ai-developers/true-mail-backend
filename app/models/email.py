from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.db_config import Base


class BulkEmailStats(Base):
    __tablename__ = "bulk_emails_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    file_name = Column(String(255))  # user can create the file name edit but by dafult file name is (test-file.csv)
    duplicate_email = Column(
        Integer
    )  # how much duplicates email in a file that is associated with table test_email and field file_id
    total_valid_emails = Column(Integer)  # how much total valid e-mail
    status = Column(Text)  # e-mail status is { completed, Cancel, Processing }
    deliverable = Column(Float)  # is e-mail deliverable
    risky = Column(Integer)  # how much total risky e-mail in file that is associalted with file_id number
    total = Column(Integer)  # total e-mail in files that is associated with file_id number
    created_at = Column(DateTime)
    soft_delete = Column(Boolean)

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
    is_risky = Column(Boolean)
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
    soft_delete = Column(Boolean)
    created_at = Column(DateTime)
    soft_delete = Column(Boolean)

    user = relationship("User", backref="test_emails")
    bulk_email_stats = relationship("BulkEmailStats", backref="test_emails")
