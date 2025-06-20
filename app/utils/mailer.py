import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

async def send_verification_email(email: str, token: str):
    """Send email verification link to user."""
    msg = MIMEMultipart()
    msg['From'] = settings.EMAILS_FROM_EMAIL
    msg['To'] = email
    msg['Subject'] = "Verify your email address"
    
    # Create verification link
    verification_link = f"{settings.FRONTEND_DOMAIN}/verify-email/{token}"
    
    # Email body
    body = f"""
    Hello,
    
    Thank you for registering with True Mail. Please click the link below to verify your email address:
    
    {verification_link}
    
    If you did not register for an account, please ignore this email.
    
    Best regards,
    True Mail Team
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Create SMTP session
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False 