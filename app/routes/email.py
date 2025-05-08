from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.models.email import BulkEmailStats, TestEmail  # Import your SQLAlchemy models
from app.models.user import User
from app.schemas.email import (  # Import your Pydantic models
    BulkEmailStatsCreate,
    BulkEmailStatsRead,
    BulkEmailStatsWithTestEmails,
    TestEmailCreate,
    TestEmailRead,
)
from app.schemas.user import UserResponse

router = APIRouter()
# User Endpoints


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Get a user by their ID.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


# # Bulk Email Stats Endpoints
# @router.post("/bulk_email_stats/", response_model=BulkEmailStatsRead, status_code=status.HTTP_201_CREATED)
# def create_bulk_email_stats(bulk_email_stats: BulkEmailStatsCreate, db: Session = Depends(get_db)):
#     """
#     Create bulk email statistics.
#     """
#     db_bulk_email_stats = BulkEmailStats(**bulk_email_stats.dict(), created_at=datetime.utcnow())
#     db.add(db_bulk_email_stats)
#     try:
#         db.commit()
#         db.refresh(db_bulk_email_stats)
#         return db_bulk_email_stats
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found")

# @router.get("/bulk_email_stats/{bulk_email_id}", response_model=BulkEmailStatsWithTestEmails)
# def get_bulk_email_stats(bulk_email_id: int, db: Session = Depends(get_db)):
#     """
#     Get bulk email statistics by ID, including associated test emails.
#     """
#     bulk_email_stats = db.query(BulkEmailStats).options().filter(BulkEmailStats.id == bulk_email_id).first() # Removed joinedload
#     if not bulk_email_stats:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulk email stats not found")

#     # Fetch associated test emails using a separate query
#     test_emails = db.query(TestEmail).filter(TestEmail.file_id == bulk_email_id).all()

#     # Combine the results
#     result = BulkEmailStatsWithTestEmails.from_orm(bulk_email_stats)  # Convert to Pydantic model
#     result.test_emails = [TestEmailRead.from_orm(email) for email in test_emails] # Convert each TestEmail to TestEmailRead
#     return result

# @router.get("/bulk_email_stats/", response_model=List[BulkEmailStatsRead])
# def get_all_bulk_email_stats(db: Session = Depends(get_db)):
#     """
#     Get all bulk email statistics.
#     """
#     bulk_email_stats = db.query(BulkEmailStats).all()
#     return bulk_email_stats


# Bulk Email Stats Endpoints
@router.post(
    "/bulk_email_stats/",
    response_model=List[BulkEmailStatsRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create Bulk Email Stats",
    description="Endpoint to create bulk email statistics.  Accepts a list of BulkEmailStatsCreate objects.",
    responses={
        201: {"description": "Bulk email stats created successfully."},
        400: {"description": "Invalid input or User ID not found."},
        500: {"description": "Internal server error."},
    },
)
def create_bulk_email_stats(
    bulk_email_stats_list: BulkEmailStatsCreate, db: Session = Depends(get_db)
):
    """
    Create bulk email statistics.  This version handles multiple entries.
    """
    db_bulk_email_stats_list = []
    for bulk_email_stats in bulk_email_stats_list.bulk_email_stats_list:
        db_bulk_email_stats = BulkEmailStats(**bulk_email_stats.dict())
        db_bulk_email_stats.created_at = datetime.utcnow()
        db.add(db_bulk_email_stats)
        db_bulk_email_stats_list.routerend(
            db_bulk_email_stats
        )  # Collect the DB objects

    try:
        db.commit()
        for db_item in db_bulk_email_stats_list:
            db.refresh(db_item)  # Refresh all
        return db_bulk_email_stats_list
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found"
        )  # Rollback


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
)
def get_bulk_email_stats(bulk_email_id: int, db: Session = Depends(get_db)):
    """
    Get bulk email statistics by ID, including associated test emails.
    """
    bulk_email_stats = (
        db.query(BulkEmailStats)
        .options()
        .filter(BulkEmailStats.id == bulk_email_id)
        .first()
    )  # Removed joinedload
    if not bulk_email_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bulk email stats not found"
        )

    # Fetch associated test emails using a separate query
    test_emails = db.query(TestEmail).filter(TestEmail.file_id == bulk_email_id).all()

    # Combine the results
    result = BulkEmailStatsWithTestEmails.from_orm(
        bulk_email_stats
    )  # Convert to Pydantic model
    result.test_emails = [
        TestEmailRead.from_orm(email) for email in test_emails
    ]  # Convert each TestEmail to TestEmailRead
    return result


@router.get(
    "/bulk_email_stats/",
    response_model=List[BulkEmailStatsRead],
    summary="Get All Bulk Email Stats",
    description="Retrieve a list of all bulk email statistics.",
    responses={
        200: {"description": "List of bulk email stats retrieved successfully."},
        500: {"description": "Internal server error."},
    },
)
def get_all_bulk_email_stats(db: Session = Depends(get_db)):
    """
    Get all bulk email statistics.
    """
    bulk_email_stats = db.query(BulkEmailStats).all()
    return bulk_email_stats


@router.post(
    "/test_email/", response_model=TestEmailRead, status_code=status.HTTP_201_CREATED
)
def create_test_email(test_email: TestEmailCreate, db: Session = Depends(get_db)):
    """
    Create a test email entry.
    """
    # Validate user_id
    user = db.query(User).filter(User.user_id == test_email.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found"
        )

    # Validate file_id if provided

    if test_email.file_id is not None:
        bulk_email_stats = (
            db.query(BulkEmailStats)
            .filter(BulkEmailStats.id == test_email.file_id)
            .first()
        )
        if not bulk_email_stats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File ID not found"
            )

    db_test_email = TestEmail(**test_email.dict())
    db_test_email.created_at = datetime.utcnow()
    db.add(db_test_email)
    try:
        db.commit()
        db.refresh(db_test_email)
        return db_test_email
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )  # Should not occur, but helpful to have.


@router.get("/test_email/{test_email_id}", response_model=TestEmailRead)
def get_test_email(test_email_id: int, db: Session = Depends(get_db)):
    """
    Get a test email by its ID.
    """
    test_email = db.query(TestEmail).filter(TestEmail.id == test_email_id).first()
    if not test_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test email not found"
        )
    return test_email


@router.get("/test_email/", response_model=List[TestEmailRead])
def get_all_test_emails(db: Session = Depends(get_db)):
    """
    Get all test emails.
    """
    test_emails = db.query(TestEmail).all()
    return test_emails
