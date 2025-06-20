from app.db.session import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status
from app.utils.response import success_response, error_response
from app.services.validator import EmailValidationService

router = APIRouter()

DEFAULT_SENDER_EMAIL = "verify@example.com"


@router.get("/verify/{email}")
async def verify_email(email: str, db: Session = Depends(get_db)):
    # TODO: Implement email verification logic
    # Example: If email is valid
    if "@" in email:
        return success_response(
            message="Email verification endpoint", data={"email": email}, status_code=status.HTTP_200_OK
        )
    else:
        return error_response(message="Invalid email address", status_code=status.HTTP_400_BAD_REQUEST)


@router.post("/send")
async def send_email(email: str):
    # TODO: Implement email sending logic
    db = Session(get_db)
    service = EmailValidationService(db)
    check = await service.homepage_email_validation(email=email, sender_email=DEFAULT_SENDER_EMAIL)
    return success_response(message="Email sending endpoint", data=check, status_code=status.HTTP_201_CREATED)
