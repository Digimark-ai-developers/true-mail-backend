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
from app.schemas.user import UserInfo, UserResponse
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/email", tags=["Email Validation Functions"])
# User Endpoints


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


# Bulk Email Endpoints
@router.post(
    "/bulk_email_stats_with_emails/upload",
    summary="Upload a file (.csv or .txt) to create bulk email stats",
    tags=["BulkEmails"],
)
def upload_bulk_email_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    # ✅ Step 1: Read and extract emails from file
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only CSV and TXT are allowed.",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file. Make sure it's properly formatted.",
        )
    finally:
        file.file.close()

    if not emails:
        raise HTTPException(
            status_code=400, detail="No valid emails found in the uploaded file."
        )

    # ✅ Step 2: Check credit
    email_count = len(emails)
    credit = db.query(Credit).filter(Credit.user_id == current_user.user_Id).first()
    if not credit or credit.remaining_credits < email_count:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient credits to test all emails",
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

    # ✅ Step 3: Create BulkEmailStats record
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
                "message": "Bulk email stats created successfully from file",
                "data": BulkEmailStatsResponseWithEmails(
                    user_id=current_user.user_Id,
                    file_id=bulk_stat.id,
                    file_name=bulk_stat.file_name,
                    test_emails=[e.user_tested_email for e in test_email_objs],
                ).dict(),
            },
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save email records",
        )


@router.post(
    "/bulk_email_stats_with_emails/",
    # response_model=BulkEmailStatsResponseWithEmails,
    status_code=status.HTTP_201_CREATED,
    summary="Create Bulk Email(Copy / Past Function) Stats with Test Emails and Deduct Credits",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


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


@router.put("/filename_update/", tags=["Bulk"])
async def update_filename(
    session: Annotated[Session, Depends(get_db)],
    old_filename: str = Query(),
    new_filename: str = Query(),
    current_user: UserInfo = Depends(get_current_user),
):
    """Updating file name"""
    db_filename = (
        session.query(BulkEmailStats)
        .filter(
            BulkEmailStats.file_name == old_filename,
            BulkEmailStats.user_id == current_user.user_Id,
        )
        .first()
    )
    if not db_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found."
        )

    db_filename.file_name = new_filename
    session.commit()
    session.refresh(db_filename)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "Message": "File name changed succesfully.",
            "data": db_filename.file_name,
        },
    )
