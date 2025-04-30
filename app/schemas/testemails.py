from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class TestEmailsBase(BaseModel):
    file_name: str
    user_tested_email: str
    valid_email: int
    Invalid_email: int
    duplicate_email: int
    email_status: str
    deliverable: str
    total: int

class TestEmailsCreate(TestEmailsBase):
    pass

class TestEmailsUpdate(BaseModel):
    file_name: Optional[str] = None
    user_tested_email: Optional[str] = None
    valid_email: Optional[int] = None
    Invalid_email: Optional[int] = None
    duplicate_email: Optional[int] = None
    email_status: Optional[str] = None
    deliverable: Optional[str] = None
    total: Optional[int] = None

class TestEmails(TestEmailsBase):
    user_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True