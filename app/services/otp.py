from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.otp import OTP
import secrets
from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings


def generate_otp(length: int = 6) -> str:
    """Generates the otp"""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def store_otp(db: Session, email: str, password: str, code: str, ttl_seconds: int = 300):
    """Stores the otp for verification"""
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    # If existing, overwrite
    otp_entry = db.query(OTP).filter_by(email=email).first()
    if otp_entry:
        otp_entry.code = code
        otp_entry.expires_at = expires
    else:
        otp_entry = OTP(email=email, code=code, password=password, expires_at=expires)
        db.add(otp_entry)

    db.commit()


async def send_otp_email(to_email: str, otp: str, ttl_seconds: int = 300):
    minutes = ttl_seconds // 60
    message = EmailMessage()
    message["From"] = settings.EMAILS_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = "Your OTP Code"
    message.set_content(
        f"Your OTP is: {otp}\n\nThis OTP is valid for {minutes} minutes. Please use it before it expires."
    )

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
