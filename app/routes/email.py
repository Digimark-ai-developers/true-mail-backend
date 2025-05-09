from datetime import datetime
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# from app.utils.email_tools import check_email_reachability, validate_email_syntax
from app.database.db_config import get_db
from app.models.credits import Credit
from app.models.email import BulkEmailStats, TestEmail  # Import your SQLAlchemy models
from app.models.user import User
from app.schemas.email import (  # Import your Pydantic models
    BulkEmailStatsCreate,
    BulkEmailStatsCreateWithEmails,
    BulkEmailStatsRead,
    BulkEmailStatsResponseWithEmails,
    BulkEmailStatsWithTestEmails,
    SimpleEmailCheckRequest,
    TestEmailCreate,
    TestEmailRead,
)
from app.schemas.user import UserInfo, UserResponse
from app.services.email_validation_service import (
    validate_and_store_email,
    validate_email_fields,
)
from app.utils.jwt_handler import get_current_user

router = APIRouter()
# User Endpoints


@router.post(
    "/bulk_email_stats_with_emails/",
    # response_model=BulkEmailStatsResponseWithEmails,
    status_code=status.HTTP_201_CREATED,
    summary="Create Bulk Email Stats with Test Emails and Deduct Credits",
    description="Creates a bulk email stats record with associated test emails, while deducting user credits per email.",
)
def create_bulk_email_stats_with_emails(
    payload: BulkEmailStatsCreateWithEmails = Body(),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    # ✅ Step 1: Validate credit availability
    email_count = len(payload.test_emails)
    credit = db.query(Credit).filter(Credit.user_id == current_user.user_Id).first()
    if not credit or credit.remaining_credits < email_count:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient credits to test all emails",
        )

    # ✅ Step 2: Create BulkEmailStats (the file)
    emails = [email.lower() for email in payload.test_emails]
    total_emails = len(emails)
    unique_emails = set(emails)
    duplicate_count = total_emails - len(unique_emails)

    # Optional: Apply actual logic if you can determine these values from email content
    total_valid = 0
    risky_count = 0
    deliverable_count = 0

    for email in emails:
        # Your own custom validation logic can go here
        if email.endswith("@gmail.com"):
            total_valid += 1
            deliverable_count += 1
        elif "test" in email:
            risky_count += 1

    deliverable_percent = (
        (deliverable_count / total_emails) * 100 if total_emails > 0 else 0
    )

    bulk_stat = BulkEmailStats(
        user_id=current_user.user_Id,
        file_name="Copy/Paste",
        duplicate_email=duplicate_count,
        total_valid_emails=total_valid,
        is_risky=False,
        deliverable=deliverable_percent,
        total=total_emails,
        created_at=datetime.utcnow(),
    )
    db.add(bulk_stat)
    db.commit()
    db.refresh(bulk_stat)

    # ✅ Step 3: Create related TestEmail entries
    test_email_objs = []
    for test_email in payload.test_emails:
        test_email_obj = TestEmail(
            user_id=bulk_stat.user_id,  # User ID from input
            file_id=bulk_stat.id,  # The bulk email stat ID (file context)
            user_tested_email=test_email,  # Email being tested
            full_name="Unknown",  # Default value
            gender="Unknown",  # Default value
            status="Pending",  # Default value
            reason="N/A",  # Default value
            domain="unknown.com",  # Default value
            is_free=False,  # Default value
            is_valid=False,  # Default value
            is_disposable=False,  # Default value
            is_deliverable=False,  # Default value
            has_tag=False,  # Default value
            alphabetical_characters=0,  # Default value
            is_mailbox_full=False,  # Default value
            has_role=False,  # Default value
            is_accept_all=False,  # Default value
            has_numerical_characters=0,  # Default value
            has_unicode_symbols=0,  # Default value
            has_no_reply=False,  # Default value
            smtp_provider="Unknown",  # Default value
            mx_record="N/A",  # Default value
            implicit_mx_record="N/A",  # Default value
            score=0,  # Default value
            created_at=datetime.utcnow(),  # Current time as default value
        )
        db.add(test_email_obj)
        test_email_objs.append(test_email_obj)

    # ✅ Step 4: Deduct credits
    credit.remaining_credits -= email_count
    credit.total_credits -= email_count
    credit.last_updated = datetime.utcnow()
    db.add(credit)

    try:
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Bulk email stats created successfully",
                "data": BulkEmailStatsResponseWithEmails(
                    user_id=current_user.user_Id,
                    file_id=bulk_stat.id,
                    file_name=bulk_stat.file_name,
                    test_emails=[email.user_tested_email for email in test_email_objs],
                ).dict(),
            },
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save email records",
        )


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


# @router.post(
#     "/test_email/", response_model=TestEmailRead, status_code=status.HTTP_201_CREATED
# )
# def create_test_email(test_email: TestEmailCreate, db: Session = Depends(get_db)):
#     """
#     Create a test email entry.
#     """
#     # Validate user_id
#     user = db.query(User).filter(User.user_id == test_email.user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found"
#         )

#     # Validate file_id if provided

#     if test_email.file_id is not None:
#         bulk_email_stats = (
#             db.query(BulkEmailStats)
#             .filter(BulkEmailStats.id == test_email.file_id)
#             .first()
#         )
#         if not bulk_email_stats:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail="File ID not found"
#             )

#     db_test_email = TestEmail(**test_email.dict())
#     db_test_email.created_at = datetime.utcnow()
#     db.add(db_test_email)
#     try:
#         db.commit()
#         db.refresh(db_test_email)
#         return db_test_email
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Database error occurred",
#         )  # Should not occur, but helpful to have.


# import your Credit model
@router.post(
    "/test_email/", response_model=TestEmailRead, status_code=status.HTTP_201_CREATED
)
def create_test_email(test_email: TestEmailCreate, db: Session = Depends(get_db)):
    """
    Create a test email entry and deduct one credit.
    """
    # Validate user_id
    user = db.query(User).filter(User.user_id == test_email.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found"
        )

    # Validate file_id
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

    # Fetch credit record
    credit = db.query(Credit).filter(Credit.user_id == test_email.user_id).first()
    if not credit or credit.remaining_credits < 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient credits to test email",
        )

    # Deduct 1 credit
    credit.remaining_credits -= 1
    credit.last_updated = datetime.utcnow()
    credit.total_credits -= 1
    credit.last_updated = datetime.utcnow()

    # 🔥 Explicitly re-add credit so SQLAlchemy tracks it
    db.add(credit)

    # Create TestEmail entry
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
        )


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
