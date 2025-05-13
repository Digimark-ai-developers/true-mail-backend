import csv
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Annotated, List

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# from app.utils.email_tools import check_email_reachability, validate_email_syntax
from app.database.db_config import get_db
from app.models.credits import Credit, CreditUsage
from app.models.email import BulkEmailStats, TestEmail  # Import your SQLAlchemy models
from app.models.user import User
from app.schemas.credits import CreditUsageBase
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
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/email", tags=["Email Validation Functions"])


# User Endpoints


@router.post("/test_email/", status_code=status.HTTP_201_CREATED)
def create_test_email(test_email: TestEmailCreate, db: Session = Depends(get_db)):
    """
    Create a test email entry and deduct one credit.
    """
    user = db.query(User).filter(User.user_id == test_email.user_id).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "User ID not found",
                "content": None,
            },
        )

    if test_email.file_id is not None:
        bulk_email_stats = (
            db.query(BulkEmailStats)
            .filter(BulkEmailStats.id == test_email.file_id)
            .first()
        )
        if not bulk_email_stats:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "File ID not found",
                    "content": None,
                },
            )

    credit = db.query(Credit).filter(Credit.user_id == test_email.user_id).first()
    if not credit or credit.remaining_credits < 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Insufficient credits to test email",
                "content": None,
            },
        )

    credit.remaining_credits -= 1
    credit.last_updated = datetime.utcnow()
    credit.total_credits -= 1
    db.add(credit)

    db_test_email = TestEmail(**test_email.dict())
    db_test_email.created_at = datetime.utcnow()
    db.add(db_test_email)
    db.commit()
    db.refresh(db_test_email)

    credit_used = CreditUsageBase(
        user_id=db_test_email.user_id,
        email_or_file_id=db_test_email.id,
        quantity_used=1,
        credits_used=1,
        created_at=datetime.now(timezone.utc),
    )
    db_credit_used = CreditUsage(**credit_used.model_dump())
    db.add(db_credit_used)

    try:
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Test email created successfully",
                "content": TestEmailRead.from_orm(db_test_email),
            },
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Database error occurred",
                "content": None,
            },
        )


@router.get("/test_email/{test_email_id}")
def get_test_email(test_email_id: int, db: Session = Depends(get_db)):
    test_email = db.query(TestEmail).filter(TestEmail.id == test_email_id).first()
    if not test_email:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Test email not found",
                "content": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "Test email retrieved successfully",
            "content": TestEmailRead.from_orm(test_email),
        },
    )


@router.get("/test_email/")
def get_all_test_emails(db: Session = Depends(get_db)):
    test_emails = db.query(TestEmail).all()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "All test emails retrieved successfully",
            "content": [TestEmailRead.from_orm(email) for email in test_emails],
        },
    )


# Bulk Email Endpoints


@router.post("/bulk_email_stats_with_emails/upload")
def upload_bulk_email_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    try:
        contents = file.file.read().decode("utf-8")
        extension = os.path.splitext(file.filename)[1].lower()
        if extension == ".csv":
            reader = csv.reader(StringIO(contents))
            emails = [
                row[0].strip().lower() for row in reader if row and row[0].strip()
            ]
        elif extension == ".txt":
            emails = [
                line.strip().lower() for line in contents.splitlines() if line.strip()
            ]
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Unsupported file type. Only CSV and TXT are allowed.",
                    "content": None,
                },
            )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Could not read the uploaded file. Make sure it's properly formatted.",
                "content": None,
            },
        )
    finally:
        file.file.close()

    if not emails:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "No valid emails found in the uploaded file.",
                "content": None,
            },
        )

    email_count = len(emails)
    credit = db.query(Credit).filter(Credit.user_id == current_user.user_Id).first()
    if not credit or credit.remaining_credits < email_count:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Insufficient credits to test all emails",
                "content": None,
            },
        )

    total_emails = len(emails)
    unique_emails = set(emails)
    duplicate_count = total_emails - len(unique_emails)
    total_valid = 0
    risky_count = 0
    deliverable_count = 0
    for email in emails:
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
        file_name=file.filename,
        duplicate_email=duplicate_count,
        total_valid_emails=total_valid,
        is_risky=risky_count > 0,
        deliverable=deliverable_percent,
        total=total_emails,
        created_at=datetime.utcnow(),
    )
    db.add(bulk_stat)
    db.commit()
    db.refresh(bulk_stat)

    test_email_objs = []
    for email in emails:
        test_email_obj = TestEmail(
            user_id=bulk_stat.user_id,
            file_id=bulk_stat.id,
            user_tested_email=email,
            full_name="Unknown",
            gender="Unknown",
            status="Pending",
            reason="N/A",
            domain="unknown.com",
            is_free=False,
            is_valid=False,
            is_disposable=False,
            is_deliverable=False,
            has_tag=False,
            alphabetical_characters=0,
            is_mailbox_full=False,
            has_role=False,
            is_accept_all=False,
            has_numerical_characters=0,
            has_unicode_symbols=0,
            has_no_reply=False,
            smtp_provider="Unknown",
            mx_record="N/A",
            implicit_mx_record="N/A",
            score=0,
            created_at=datetime.utcnow(),
        )
        db.add(test_email_obj)
        test_email_objs.append(test_email_obj)

    credit.remaining_credits -= email_count
    credit.total_credits -= email_count
    credit.last_updated = datetime.utcnow()
    db.add(credit)

    credit_used = CreditUsageBase(
        user_id=current_user.user_Id,
        email_or_file_id=bulk_stat.id,
        quantity_used=email_count,
        credits_used=email_count,
        created_at=datetime.now(timezone.utc),
    )
    db_credit_used = CreditUsage(**credit_used.model_dump())
    db.add(db_credit_used)

    try:
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Bulk email stats created successfully from file",
                "content": BulkEmailStatsResponseWithEmails(
                    user_id=current_user.user_Id,
                    file_id=bulk_stat.id,
                    file_name=bulk_stat.file_name,
                    test_emails=[e.user_tested_email for e in test_email_objs],
                ).dict(),
            },
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Could not save email records",
                "content": None,
            },
        )


@router.post("/bulk_email_stats_with_emails/", status_code=status.HTTP_201_CREATED)
def create_bulk_email_stats_with_emails(
    payload: BulkEmailStatsCreateWithEmails = Body(),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    email_count = len(payload.test_emails)
    credit = db.query(Credit).filter(Credit.user_id == current_user.user_Id).first()
    if not credit or credit.remaining_credits < email_count:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "Insufficient credits to test all emails",
                "content": None,
            },
        )

    emails = [email.lower() for email in payload.test_emails]
    total_emails = len(emails)
    unique_emails = set(emails)
    duplicate_count = total_emails - len(unique_emails)
    total_valid = 0
    risky_count = 0
    deliverable_count = 0
    for email in emails:
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
        is_risky=risky_count > 0,
        deliverable=deliverable_percent,
        total=total_emails,
        created_at=datetime.utcnow(),
    )
    db.add(bulk_stat)
    db.commit()
    db.refresh(bulk_stat)

    test_email_objs = []
    for test_email in payload.test_emails:
        test_email_obj = TestEmail(
            user_id=bulk_stat.user_id,
            file_id=bulk_stat.id,
            user_tested_email=test_email,
            full_name="Unknown",
            gender="Unknown",
            status="Pending",
            reason="N/A",
            domain="unknown.com",
            is_free=False,
            is_valid=False,
            is_disposable=False,
            is_deliverable=False,
            has_tag=False,
            alphabetical_characters=0,
            is_mailbox_full=False,
            has_role=False,
            is_accept_all=False,
            has_numerical_characters=0,
            has_unicode_symbols=0,
            has_no_reply=False,
            smtp_provider="Unknown",
            mx_record="N/A",
            implicit_mx_record="N/A",
            score=0,
            created_at=datetime.utcnow(),
        )
        db.add(test_email_obj)
        test_email_objs.append(test_email_obj)

    credit.remaining_credits -= email_count
    credit.total_credits -= email_count
    credit.last_updated = datetime.utcnow()
    db.add(credit)

    credit_used = CreditUsageBase(
        user_id=current_user.user_Id,
        email_or_file_id=bulk_stat.id,
        quantity_used=email_count,
        credits_used=email_count,
        created_at=datetime.now(timezone.utc),
    )
    db_credit_used = CreditUsage(**credit_used.model_dump())
    db.add(db_credit_used)

    try:
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Bulk email stats created successfully",
                "content": BulkEmailStatsResponseWithEmails(
                    user_id=current_user.user_Id,
                    file_id=bulk_stat.id,
                    file_name=bulk_stat.file_name,
                    test_emails=[e.user_tested_email for e in test_email_objs],
                ).dict(),
            },
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Could not save email records",
                "content": None,
            },
        )


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "User not found",
                "content": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "User retrieved successfully",
            "content": UserResponse.from_orm(user),
        },
    )


@router.post("/bulk_email_stats/", status_code=status.HTTP_201_CREATED)
def create_bulk_email_stats(
    bulk_email_stats_list: BulkEmailStatsCreate, db: Session = Depends(get_db)
):
    db_bulk_email_stats_list = []
    for bulk_email_stats in bulk_email_stats_list.bulk_email_stats_list:
        db_bulk_email_stats = BulkEmailStats(**bulk_email_stats.dict())
        db_bulk_email_stats.created_at = datetime.utcnow()
        db.add(db_bulk_email_stats)
        db_bulk_email_stats_list.append(db_bulk_email_stats)

    try:
        db.commit()
        for db_item in db_bulk_email_stats_list:
            db.refresh(db_item)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Bulk email stats created successfully",
                "content": [
                    BulkEmailStatsRead.from_orm(item)
                    for item in db_bulk_email_stats_list
                ],
            },
        )
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "User ID not found",
                "content": None,
            },
        )


@router.get("/bulk_email_stats/{bulk_email_id}")
def get_bulk_email_stats(bulk_email_id: int, db: Session = Depends(get_db)):
    bulk_email_stats = (
        db.query(BulkEmailStats).filter(BulkEmailStats.id == bulk_email_id).first()
    )
    if not bulk_email_stats:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Bulk email stats not found",
                "content": None,
            },
        )

    test_emails = db.query(TestEmail).filter(TestEmail.file_id == bulk_email_id).all()

    result = BulkEmailStatsWithTestEmails.from_orm(bulk_email_stats)
    result.test_emails = [TestEmailRead.from_orm(email) for email in test_emails]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "Bulk email stats retrieved successfully",
            "content": result,
        },
    )


@router.get("/bulk_email_stats/")
def get_all_bulk_email_stats(db: Session = Depends(get_db)):
    bulk_email_stats = db.query(BulkEmailStats).all()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "List of bulk email stats retrieved successfully",
            "content": [BulkEmailStatsRead.from_orm(stat) for stat in bulk_email_stats],
        },
    )


@router.put("/filename_update/")
async def update_filename(
    session: Annotated[Session, Depends(get_db)],
    old_filename: str = Query(),
    new_filename: str = Query(),
    current_user: UserInfo = Depends(get_current_user),
):
    db_filename = (
        session.query(BulkEmailStats)
        .filter(
            BulkEmailStats.file_name == old_filename,
            BulkEmailStats.user_id == current_user.user_Id,
        )
        .first()
    )

    if not db_filename:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "File not found",
                "content": None,
            },
        )

    db_filename.file_name = new_filename
    session.commit()
    session.refresh(db_filename)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status_code": status.HTTP_202_ACCEPTED,
            "message": "File name changed successfully",
            "content": {"file_name": db_filename.file_name},
        },
    )
