from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from app.database.db_config import get_db
from app.models.email import BulkEmailStats, TestEmail  # Import your SQLAlchemy models
from app.models.user import User
from app.schemas.email import (  # Import your Pydantic models
    BulkEmailStatsWithTestEmails,
    TestEmailCreate,
    TestEmailRead,
    BulkEmailStatsCreateWithEmails,
)
from app.schemas.user import UserResponse, UserInfo
from app.utils.jwt_handler import get_current_user
from app.services.email_service import (
    create_bulk_email_stats,
    get_bulk_email_stats_by_id,
    create_single_email,
    create_bulk_email_stats_from_file,
)

router = APIRouter()


# User Endpoints
@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Get a user by their ID.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# Bulk Email Endpoints
@router.post(
    "/bulk_email_stats_with_emails/upload",
    summary="Upload a file (.csv or .txt) to create bulk email stats",
    tags=["BulkEmails"],
)
def upload_bulk_email_file(
    file: UploadFile = File(...), db: Session = Depends(get_db), current_user: UserInfo = Depends(get_current_user)
):
    return create_bulk_email_stats_from_file(db=db, current_user=current_user, file=file)


@router.post(
    "/bulk_email_stats_with_emails/(Copy/Paste)/",
    status_code=status.HTTP_201_CREATED,
    summary="Create Bulk Email Stats with Test Emails and Deduct Credits",
    description="Creates a bulk email stats record with associated test emails, while deducting user credits per email.",
    tags=["BulkEmails"],
)
def create_bulk_email_stats_with_emails(
    payload: BulkEmailStatsCreateWithEmails = Body(),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    return create_bulk_email_stats(db, current_user, payload)


@router.get(
    "/bulk_email_stats/{bulk_email_id}",
    response_model=BulkEmailStatsWithTestEmails,
    summary="Get Bulk Email Stats by ID",
    description="Retrieve bulk email statistics by its unique ID, including associated test emails.",
    responses={
        200: {"description": "Bulk email stats retrieved successfully."},
        404: {"description": "Bulk email stats not found."},
        500: {"description": "Internal server error."},
    },
    tags=["BulkEmails"],
)
def get_bulk_email_stats(
    bulk_email_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    Get bulk email statistics by ID, including associated test emails.
    """
    return get_bulk_email_stats_by_id(bulk_email_id, db)


@router.get(
    "/bulk_email_stats/",
    # response_model=List[BulkEmailStatsWithTestEmails],
    summary="Get All Bulk Email Stats with Test Emails",
    description="Retrieve a list of all bulk email statistics including their associated test emails.",
    responses={
        200: {"description": "List of bulk email stats retrieved successfully."},
        500: {"description": "Internal server error."},
    },
    tags=["BulkEmails"],
)
def get_all_bulk_email_stats(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    try:
        bulk_email_stats = db.query(BulkEmailStats).options(joinedload(BulkEmailStats.test_emails)).all()
        bulk_emails_dict = jsonable_encoder(bulk_email_stats)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Bulk email stats read successfully", "data": bulk_emails_dict},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# import your Credit model
@router.post(
    "/test_email/",
    status_code=status.HTTP_201_CREATED,
    tags=["SingleEmails"],
)
def create_test_email(test_email: TestEmailCreate, db: Session = Depends(get_db)):
    """
    Create a test email entry and deduct one credit.
    """
    return create_single_email(test_email, db)


@router.get(
    "/test_email/{test_email_id}",
    response_model=TestEmailRead,
    tags=["SingleEmails"],
)
def get_test_email(
    test_email_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    Get a test email by its ID.
    """
    test_email = db.query(TestEmail).filter(TestEmail.id == test_email_id).first()
    if not test_email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test email not found")
    test_email_dict = jsonable_encoder(test_email)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Test email found successfully", "data": test_email_dict},
    )


@router.get(
    "/test_email/",
    response_model=List[TestEmailRead],
    tags=["SingleEmails"],
)
def get_all_test_emails(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """
    Get all test emails.
    """
    test_emails = db.query(TestEmail).all()
    test_emails_dict = jsonable_encoder(test_emails)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Test emails read successfully", "data": test_emails_dict},
    )
