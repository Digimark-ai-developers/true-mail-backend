# app/schemas/email.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    total: int
    soft_delete: bool
    created_at: datetime


class TestEmailBase(BaseModel):
    user_tested_email: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    domain: Optional[str] = None

    is_free: Optional[bool] = None
    is_risky: Optional[bool] = None
    is_valid: Optional[bool] = None
    is_disposable: Optional[bool] = None
    is_deliverable: Optional[bool] = None
    has_tag: Optional[bool] = None
    is_mailbox_full: Optional[bool] = None
    has_role: Optional[bool] = None
    is_accept_all: Optional[bool] = None
    has_no_reply: Optional[bool] = None

    alphabetical_characters: Optional[int] = None
    has_numerical_characters: Optional[int] = None
    has_unicode_symbols: Optional[int] = None
    score: Optional[int] = None

    smtp_provider: Optional[str] = None
    mx_record: Optional[str] = None
    implicit_mx_record: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TestEmailWrapper(BaseModel):
    message: str
    status: int
    test_id: Optional[str] = None
    data: Optional[TestEmailBase] = None


class TestEmailResponse(BaseModel):
    id: int
    user_tested_email: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None  # available
    reason: Optional[str] = None
    domain: str  # available
    is_free: bool  # available
    is_risky: Optional[bool] = None  # available
    is_valid: bool  # available
    is_disposable: bool  # available
    is_deliverable: bool  # available
    has_tag: bool
    alphabetical_characters: int  # available
    is_mailbox_full: bool
    has_role: bool
    is_accept_all: bool
    has_numerical_characters: int  # available
    has_unicode_symbols: int  # available
    has_no_reply: bool
    smtp_provider: Optional[str] = None  # available
    mx_record: Optional[str] = None
    implicit_mx_record: Optional[str] = None  # available
    score: int  # available

    model_config = ConfigDict(from_attributes=True)  # Pydantic v2 replacement for orm_mode=True


class TestEmailResponseWrapper(BaseModel):
    message: str
    status: int
    data: TestEmailResponse


class dowloadFileWrapper(BaseModel):
    message: str
    status: int
    data: List[TestEmailResponse]


class AllTestEmaislByUserId(BaseModel):
    message: str
    status: int
    data: List[TestEmailResponse]


class AllTestEmailsByFileResponse(BaseModel):
    file_id: int
    file_name: str
    emails: List[TestEmailResponse]

    model_config = ConfigDict(from_attributes=True)


class AllTestEmailsByFileResponseWrapper(BaseModel):
    message: str
    status: int
    data: List[AllTestEmailsByFileResponse]


class FileStatsResponse(BaseModel):
    id: int
    file_name: str
    total: int
    duplicates: int
    deliverable: int
    undeliverable: int
    risky: int
    status: str
    duplicated_percentage: float
    deliverable_percentage: float
    undeliverable_percentage: float
    risky_percentage: float
    uploaded_at: datetime


class FileStatsResponseWrapper(BaseModel):
    message: str
    status: int
    data: FileStatsResponse


# Models for creating data (request bodies)
class BulkEmailStatsCreate(BulkEmailStatsBase):
    user_id: str  # Make user_id required for creation


# class TestEmailCreate(TestEmailBase):
#     file_id: Optional[int] = None


# Models for reading data (response bodies)
class BulkEmailStatsRead(BulkEmailStatsBase):
    id: int
    user_id: str

    model_config = ConfigDict(from_attributes=True)


# Model for User. Pydantic model representation
class UserRead(BaseModel):
    user_id: str
    # Add other fields as necessary


class SimpleEmailCheckRequest(BaseModel):
    user_tested_email: str


class CreditUsageBase(BaseModel):
    """Base model for credit usage"""

    user_id: str
    email_or_file_id: int
    quantity_used: int
    credits_used: int
    created_at: datetime


class BulkEmailStatsCreateWithEmails(BaseModel):
    test_emails: List[str] = Field(..., description="List of email addresses to be tested")

    class Config:
        json_schema_extra = {
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
    test_emails: list[TestEmailBase]

class BulkEmailResponseWrapper(BaseModel):
    message: str
    status: int
    task_id: Optional[str] = None
    data: Optional[BulkEmailStatsResponseWithEmails] = None



class FileStats(BaseModel):
    id: int
    file_name: str
    total_emails: int
    deliverable: int
    status: str


class FileStatsResponse(BaseModel):
    message: str
    status: int
    data: List[FileStats]


class AllTestEmaislOrderedByCreationTime(BaseModel):
    message: str
    status: int
    data: List[TestEmailResponse]
