import csv, os
from io import StringIO
from datetime import datetime

from fastapi import HTTPException, status, Body
from fastapi import UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.credits import Credit
from app.models.email import BulkEmailStats, TestEmail  # Import your SQLAlchemy models
from app.models.user import User
from app.schemas.email import (  # Import your Pydantic models
    BulkEmailStatsWithTestEmails,
    TestEmailCreate,
    TestEmailRead,
    BulkEmailStatsCreateWithEmails,
    BulkEmailStatsResponseWithEmails,
)
from app.schemas.user import UserInfo


# Bulk email serivces


def create_bulk_email_stats_from_file(
    db: Session,
    current_user: UserInfo,
    file: UploadFile = File(...)
):
    # ✅ Step 1: Read and extract emails from file
    try:
        contents = file.file.read().decode("utf-8")
        extension = os.path.splitext(file.filename)[1].lower()

        if extension == ".csv":
            reader = csv.reader(StringIO(contents))
            emails = [row[0].strip().lower() for row in reader if row and row[0].strip()]
        elif extension == ".txt":
            emails = [line.strip().lower() for line in contents.splitlines() if line.strip()]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only CSV and TXT are allowed."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file. Make sure it's properly formatted."
        )
    finally:
        file.file.close()

    if not emails:
        raise HTTPException(status_code=400, detail="No valid emails found in the uploaded file.")

    # ✅ Step 2: Check credit
    email_count = len(emails)
    credit = db.query(Credit).filter(Credit.user_id == current_user.user_Id).first()
    if not credit or credit.remaining_credits < email_count:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient credits to test all emails"
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

    deliverable_percent = (deliverable_count / total_emails) * 100 if total_emails > 0 else 0

    # ✅ Step 3: Create BulkEmailStats record
    bulk_stat = BulkEmailStats(
        user_id=current_user.user_Id,
        file_name=file.filename,
        duplicate_email=duplicate_count,
        total_valid_emails=total_valid,
        is_risky=risky_count > 0,
        deliverable=deliverable_percent,
        total=total_emails,
        created_at=datetime.utcnow()
    )
    db.add(bulk_stat)
    db.commit()
    db.refresh(bulk_stat)

    # ✅ Step 4: Create TestEmail entries
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

    # ✅ Step 5: Deduct credits
    credit.remaining_credits -= email_count
    credit.total_credits -= email_count
    credit.last_updated = datetime.utcnow()
    db.add(credit)

    try:
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Bulk email stats created successfully from file",
                "data": BulkEmailStatsResponseWithEmails(
                    user_id=current_user.user_Id,
                    file_id=bulk_stat.id,
                    file_name=bulk_stat.file_name,
                    test_emails=[e.user_tested_email for e in test_email_objs],
                ).dict()
            }
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save email records"
        )


def create_bulk_email_stats(
    db: Session,
    current_user: UserInfo,
    payload: BulkEmailStatsCreateWithEmails = Body(),
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

    deliverable_percent = (deliverable_count / total_emails) * 100 if total_emails > 0 else 0

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

def get_bulk_email_stats_by_id(bulk_email_id: int, db: Session):
    """
    Get bulk email statistics by ID, including associated test emails.
    """
    bulk_email_stats = (
        db.query(BulkEmailStats).options().filter(BulkEmailStats.id == bulk_email_id).first()
    )  # Removed joinedload
    if not bulk_email_stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulk email stats not found")

    # Fetch associated test emails using a separate query
    test_emails = db.query(TestEmail).filter(TestEmail.file_id == bulk_email_id).all()

    # Combine the results
    result = BulkEmailStatsWithTestEmails.from_orm(bulk_email_stats)  # Convert to Pydantic model
    result.test_emails = [
        TestEmailRead.from_orm(email) for email in test_emails
    ]  # Convert each TestEmail to TestEmailRead
    result_dict = jsonable_encoder(result)
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Bulk email stat found successfully",
                "data": result_dict
            },
        )

# Single Email Services

def create_single_email(test_email: TestEmailCreate, db: Session):
    """
    Create a test email entry and deduct one credit.
    """
    # Validate user_id
    user = db.query(User).filter(User.user_id == test_email.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found")

    # Validate file_id
    if test_email.file_id is not None:
        bulk_email_stats = db.query(BulkEmailStats).filter(BulkEmailStats.id == test_email.file_id).first()
        if not bulk_email_stats:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File ID not found")

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
        db_test_email_dict = jsonable_encoder(db_test_email)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Test email created successfully",
                "data": db_test_email_dict
            },
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )