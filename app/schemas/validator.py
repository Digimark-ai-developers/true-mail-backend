from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# Single email validation schemas
class GeneralInfo(BaseModel):
    """Sub reader for EmailValidationData"""

    full_name: str
    gender: str
    status: str
    reason: str
    domain: str


class Details(BaseModel):
    """Sub reader for EmailValidationData"""

    is_free: bool
    has_role: bool
    disposable: bool
    accept_all: bool
    has_tag: bool
    numerical_characters: int
    alphabetical_characters: int
    unicode_symbols: int
    is_mailbox_full: bool
    is_no_reply: bool


class MailServerInformation(BaseModel):
    """Sub reader for EmailValidationData"""

    smtp_provider: str
    mx_record: str
    implicit_mx_record: str


class EmailValidationData(BaseModel):
    """Reads the data from storage"""

    validated_email: str
    file_id: Optional[int]
    score: float
    general: GeneralInfo
    details: Details
    mail_server_information: MailServerInformation


# FIle email validations schemas
class FileEmailValidationData(BaseModel):
    """Reads data from backend in the defined format"""

    user_id: int
    file_id: int
    file_name: str
    emails: list[EmailValidationData]


class FileValidationEmailsCreate(BaseModel):
    """Reads and creates data for storage"""

    file_name: Optional[str] = None
    validate_emails: list[str] = Field(..., description="List of email addresses to be validated")


class FileGraph(BaseModel):
    """Graph breakdown for each status"""

    status: str
    total: int
    fill: str


class FileData(BaseModel):
    """Individual file data"""

    file_id: int
    file_name: str
    file_status: str
    graph: list[FileGraph]


class StatItem(BaseModel):
    status: str  # e.g., "deliverable", "risky", etc.
    emails: int
    fill: str  # e.g., "var(--color-deliverable)"


class EmailInfo(BaseModel):
    email_id: int
    email: str
    reason: str
    score: float
    status: str


class FileStatsSchema(BaseModel):
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

    deliverable_emails: list[StatItem]
    conversion_graph: list[StatItem]
    emails: list[EmailInfo]


class FileDeletion(BaseModel):
    """Display's deletion message for files"""

    file_name: str
    emails: list[str]
