from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey
from app.database.db_config import Base

class BulkEmails(Base):
    __tablename__ = 'bulk_emails'
    
    email_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('User.user_Id'), nullable=False)  # Proper foreign key
    user_emails = Column(String, nullable=False)  # Stores actual email content (e.g., "test@example.com")
    created_at = Column(DateTime(timezone=False), nullable=False)
    valid_email = Column(Integer, nullable=False)
    invalid_email = Column(Integer, nullable=False)  # Lowercase for consistency
    file_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    deliverable = Column(String, nullable=False)
    total = Column(Integer, nullable=False)
    valid = Column(Integer, nullable=False)
    invalid = Column(Integer, nullable=False)