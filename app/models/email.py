from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database.db_config import Base


class BulkEmailStats(Base):
    __tablename__ = 'bulk_emails_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('user.user_id'))
    file_name = Column(String(255))
    user_tested_email = Column(Text)
    duplicate_email = Column(Integer)  # how much duplicates in a file i numbers
    total_valid_emails = Column(Integer)
    email_status = Column(Text)
    deliverable = Column(Float)
    is_risky = Column(Boolean)
    total = Column(Integer)
    created_at = Column(DateTime)

    user = relationship('User', backref='bulk_emails_stats')


class TestEmail(Base):
    __tablename__ = 'test_email'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('user.user_id'))
    file_id = Column(Integer, ForeignKey('bulk_emails_stats.id'), nullable=True)
    user_tested_email = Column(Text)
    full_name = Column(String(255)) # Full name of user
    gender = Column(String) # Geneder of user
    status = Column(String) # is e-mail in a deliverable state
    reason = Column(String) # Accepted e-mail
    domain = Column(String(255)) # e-mail domain e.g. google, yahoo
    is_free = Column(Boolean) # is free
    is_valid = Column(Boolean)  # is e-mail valid or invalid
    is_disposable = Column(Boolean) # is that e-mail DEA
    is_deliverable = Column(Boolean) # is the e-mail deliverable or not
    has_tag = Column(Boolean)
    alphabetical_characters = Column(Integer) # how many aplphabetical characters does the e-mail have
    is_mailbox_full = Column(Boolean) # is the mailbox full or not
    has_role = Column(Boolean) # does the e-mail have a roll like support@
    is_accept_all = Column(Boolean) # is that e-mail server acceptable 
    has_numerical_characters = Column(Integer) # how many numerical characters does the e-mail have
    has_unicode_symbols = Column(Integer) # does the e-mail have any unique characters 
    has_no_reply = Column(Boolean) # an address that implies that it replies or not
    smtp_provider = Column(String(255)) # like microsoft etc.
    mx_record = Column(String(255))
    implicit_mx_record = Column(String(255))
    score = Column(Integer)
    created_at = Column(DateTime) # when was this email created at

    user = relationship('User', backref='test_emails')
    bulk_email_stats = relationship('BulkEmailStats', backref='test_emails')
