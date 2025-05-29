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


class BulkEmailStatsResponseWithEmails(BaseModel):
    user_id: str
    file_id: int
    file_name: str
    test_emails: List[TestEmailBase]  # List of validated emails


class BulkEmailStatsWrapper(BaseModel):
    message: str
    status: int
    task_id: Optional[str] = None
    data: Optional[BulkEmailStatsResponseWithEmails] = None


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
    status: Optional[str] = None
    reason: Optional[str] = None
    domain: Optional[str] = None  # changed to Optional
    is_free: Optional[bool] = None  # changed to Optional
    is_risky: Optional[bool] = None
    is_valid: Optional[bool] = None  # changed to Optional
    is_disposable: Optional[bool] = None  # changed to Optional
    is_deliverable: Optional[bool] = None  # changed to Optional
    has_tag: Optional[bool] = None  # changed to Optional
    alphabetical_characters: Optional[int] = None  # changed to Optional
    is_mailbox_full: Optional[bool] = None  # changed to Optional
    has_role: Optional[bool] = None  # changed to Optional
    is_accept_all: Optional[bool] = None  # changed to Optional
    has_numerical_characters: Optional[int] = None
    has_unicode_symbols: Optional[int] = None
    has_no_reply: Optional[bool] = None  # changed to Optional
    smtp_provider: Optional[str] = None
    mx_record: Optional[str] = None
    implicit_mx_record: Optional[str] = None
    score: Optional[int] = None  # changed to Optional

    model_config = ConfigDict(from_attributes=True)


class TestEmailResponseWrapper(BaseModel):
    message: str
    status: int
    data: TestEmailResponse


class dowloadFileWrapper(BaseModel):
    message: str
    status: int
    data: List[TestEmailResponse]

class BulkEmailUploadRequest(BaseModel):
    file_name: str
    file_content: str  # plain text with newlines

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
    status: Optional[str]
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
    file_name: Optional[str] = None
    test_emails: List[str] = Field(..., description="List of email addresses to be tested")

    class Config:
        json_schema_extra = {
            "example": {
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
    file_name: Optional[str] = None
    total_emails: Optional[int] = None
    deliverable: Optional[int] = None
    status: Optional[str] = None


class FileStatsResponse(BaseModel):
    message: str
    status: int
    data: List[FileStats]


class AllTestEmaislOrderedByCreationTime(BaseModel):
    message: str
    status: int
    data: List[TestEmailResponse]
