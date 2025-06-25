# models/otp.py
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from app.db.session import Base


class OTP(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, unique=True)
    password = Column(String)  # Store hashed password
    code = Column(Integer)
    expires_at = Column(DateTime)

    def is_expired(self):
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # Assume UTC if no timezone info
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at
