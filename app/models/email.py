# app/models/email.py
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
    file_name = Column(String(255))  #
    user_tested_email = Column(Text)  # which e-mials are tested by user id
    duplicate_email = Column(Integer)  # how much duplicates in a file i numbers
    total_valid_emails = Column(Integer)  # how much total valid e-mail
    email_status = Column(Text)  #  e-mail status is { completed, Cancel, Processing }
    deliverable = Column(Float)  # is e-mail deliverable
    is_risky = Column(Boolean)  # is that e-mail is risky
    total = Column(Integer)  # total e-mail in files are check
    created_at = Column(DateTime)

    user = relationship("User", backref="bulk_emails_stats")


class TestEmail(Base):
    __tablename__ = "test_email"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    file_id = Column(Integer, ForeignKey("bulk_emails_stats.id"), nullable=True)
    user_tested_email = Column(Text)  # which e-mials are tested by user id
    full_name = Column(String(255))  # user full name
    gender = Column(String)  # user Gender
    status = Column(String)  # e-mail status is { completed, Cancel, Processing }
    reason = Column(String)  # Accepeted e-mail
    domain = Column(String(255))  # e-mail domain e.g google, yahoo,
    is_free = Column(Boolean)  # is free
    is_valid = Column(Boolean)  # is e-mail valid or invalid
    is_disposable = Column(Boolean)  # is that e-mail DEA
    is_deliverable = Column(Boolean)  # is e-mail deliverable
    has_tag = Column(Boolean)  # e-mail has tag appended like username+tag.gmail.com
    alphabetical_characters = Column(
        Integer
    )  # how much alphabatical characters in per email
    is_mailbox_full = Column(Boolean)  #
    has_role = Column(Boolean)  #  an e-mail address has role like support@teammail.com
    is_accept_all = Column(Boolean)  # is that e-mail server accepetable
    has_numerical_characters = Column(Integer)  # is e-mail has numaric characters
    has_unicode_symbols = Column(Integer)  # is e-mail has unicode
    has_no_reply = Column(Boolean)  # an address has indicates in should no reply
    smtp_provider = Column(String(255))  # like Microsoft etc
    mx_record = Column(
        String(255)
    )  # like digimarkdevelopers-com.mail.protection.mailtitan.com
    implicit_mx_record = Column(String(255))  # implicit mx record
    score = Column(Integer)  # e-mail socre
    created_at = Column(DateTime)

    user = relationship("User", backref="test_emails")
    bulk_email_stats = relationship("BulkEmailStats", backref="test_emails")
