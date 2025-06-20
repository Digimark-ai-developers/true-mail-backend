from typing import Optional
from pydantic import BaseModel


class GeneralInfo(BaseModel):
    full_name: str
    gender: str
    status: str
    reason: str
    domain: str


class Details(BaseModel):
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
    smtp_provider: str
    mx_record: str
    implicit_mx_record: str


class EmailValidationData(BaseModel):
    validated_email: str
    file_id: Optional[int]
    score: float
    general: GeneralInfo
    details: Details
    mail_server_information: MailServerInformation
