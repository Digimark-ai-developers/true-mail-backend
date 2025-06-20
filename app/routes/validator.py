import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

# from app.utils.email_tools import check_email_reachability, validate_email_syntax
from app.models.validator import SingleValidation, FileValidation
from app.dependencies.auth import get_current_user, UserInfo
from app.utils.response import success_response, error_response, single_email_validation_response
from app.services.validator import EmailValidationService
from app.utils.cache import (
    single_email_validation_status_cache,
    file_emails_validation_status_cache,
    copy_paste_email_validation_status_cache,
)
from app.utils.validator import load_disposable_domains

router = APIRouter()

DEFAULT_SENDER_EMAIL = "verify@example.com"
DISPOSABLE_DOMAINS = load_disposable_domains()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/single_email", response_model=success_response)
async def create_single_email(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    test_id = str(uuid.uuid4())
    single_email_validation_status_cache[test_id] = {"status": "processing"}

    service = EmailValidationService(db)
    background_tasks.add_task(service.create_email_validation, user.user_id, email, test_id)

    return success_response(
        message="Email test started. Check back shortly.",
        status_code=status.HTTP_202_ACCEPTED,
        data=test_id,
    )


@router.get("/single_email_status/{test_id}", response_model=success_response)
def get_validate_email_status(test_id: str, db: Session = Depends(get_db), user: UserInfo = Depends(get_current_user)):
    task = single_email_validation_status_cache.get(test_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task status not found")

    if task["status"] == "completed":
        email = db.query(SingleValidation).filter(SingleValidation.id == task["email_id"]).first()
        return success_response(
            message=task["message"],
            status_code=status.HTTP_200_OK,
            data=single_email_validation_response(email).model_dump(),
        )

    elif task["status"] == "failed":
        raise HTTPException(status_code=500, detail=task["error"])

    return success_response(
        message="Still working...", status_code=status.HTTP_202_ACCEPTED, data={"test_id": test_id, "data": None}
    )


@router.get("/single_email/{validated_email_id}", response_model=success_response)
def get_single_validated_email(
    validated_email_id: int, db: Session = Depends(get_db), user: UserInfo = Depends(get_current_user)
):
    """
    Retrieve a single tested email by its ID.

    Args:

        email_id (int): ID of the validated email to retrieve.

    Returns:

        JSONResponse: The validated email data.

    Raises:

        HTTPException: If the email with given ID is not found.
    """
    service = EmailValidationService(db)
    validated_email = service.get_test_email(validated_email_id, user.user_id)

    return success_response(
        message="Test email found successfully.",
        status_code=status.HTTP_302_FOUND,
        data=single_email_validation_response(validated_email).model_dump(),
    )


@router.get("/recent_validated_emails", response_model=success_response)
async def get_all_recent_validated_emails(db: Session = Depends(get_db), user: UserInfo = Depends(get_current_user)):
    """
    Get all validated emails ordered by creation time.

    Returns:

        JSONResponse: List of all validated emails.
    """
    service = EmailValidationService(db)
    validated_emails = service.get_emails_by_creation_time(user.user_id)
    return success_response(
        message="Emails fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=[single_email_validation_response(email).model_dump() for email in validated_emails],
    )


@router.get("/all_validated_emails", response_model=success_response)
def get_all_single_validated_emails_by_user_id(
    db: Session = Depends(get_db), user: UserInfo = Depends(get_current_user)
):
    """
    Get all validated emails for the current user.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of emails validated by the user.
    """
    service = EmailValidationService(db)
    validated_emails = service.get_all_test_emails(user.user_id)
    return success_response(
        message="All test emails read successfully.",
        status_code=status.HTTP_200_OK,
        data=[single_email_validation_response(email).model_dump() for email in validated_emails],
    )
