# app/schemas/email.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# Base models (for shared fields)
class UserBase(BaseModel):
    user_id: str


class BulkEmailStatsBase(BaseModel):
    file_name: str
    user_tested_email: Optional[str] = None  # Added can be None for testing purposes
    duplicate_email: int
    total_valid_emails: int
    email_status: Optional[str] = None  # Added can be None for testing purposes
    deliverable: float
    is_risky: bool
    total: int
    soft_delete: bool
    created_at: datetime


class TestEmailBase(BaseModel):
    user_tested_email: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    domain: str
    is_free: bool
    is_valid: bool
    is_disposable: bool
    is_deliverable: bool
    has_tag: bool
    alphabetical_characters: int
    is_mailbox_full: bool
    has_role: bool
    is_accept_all: bool
    has_numerical_characters: int
    has_unicode_symbols: int
    has_no_reply: bool
    smtp_provider: Optional[str] = None
    mx_record: Optional[str] = None
    implicit_mx_record: Optional[str] = None
    score: int
    soft_delete: bool


# Models for creating data (request bodies)
class BulkEmailStatsCreate(BulkEmailStatsBase):
    user_id: str  # Make user_id required for creation


class TestEmailCreate(TestEmailBase):
    user_id: str
    file_id: Optional[int] = None


# Models for reading data (response bodies)
class BulkEmailStatsRead(BulkEmailStatsBase):
    id: int
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class TestEmailRead(TestEmailBase):
    id: int
    user_id: str
    file_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Model for User. Pydantic model representation
class UserRead(BaseModel):
    user_id: str
    # Add other fields as necessary


# Model for list of test emails for Bulk Email Stats
class TestEmailList(BaseModel):
    test_emails: List[TestEmailRead]


# Model to include TestEmailList and BulkEmailStatsRead
class BulkEmailStatsWithTestEmails(BulkEmailStatsRead):
    test_emails: List[TestEmailRead]

    model_config = ConfigDict(from_attributes=True)


class SimpleEmailCheckRequest(BaseModel):
    user_tested_email: str


class BulkEmailStatsCreateWithEmails(BaseModel):
    test_emails: List[str] = Field(..., description="List of email addresses to be tested")

    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "file_name": "marketing_emails_may.csv",
                "test_emails": [
                    "john@example.com",
                    "jane@example.com",
                    "john@example.com",
                ],
            }
        }


class BulkEmailStatsResponseWithEmails(BaseModel):
    user_id: str
    file_id: int
    file_name: str
    test_emails: list[str]
