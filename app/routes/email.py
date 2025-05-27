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
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# from app.utils.email_tools import check_email_reachability, validate_email_syntax
from app.database.db_config import get_db
from app.models.email import TestEmail
from app.schemas.auth import UserID
from app.schemas.email import (
    AllTestEmailsByFileResponseWrapper,
    AllTestEmaislByUserId,
    AllTestEmaislOrderedByCreationTime,
    FileStatsResponse,
    FileStatsResponseWrapper,
    SimpleEmailCheckRequest,
    TestEmailResponse,
    TestEmailResponseWrapper,
    TestEmailWrapper,
    dowloadFileWrapper,
)
from app.schemas.email import (  # Import your Pydantic models
    BulkEmailStatsCreateWithEmails,
    BulkEmailStatsRead,
)
from app.schemas.user import UserInfo
from app.utils.jwt_handler import get_current_user
from app.services.email_service import EmailService
from app.utils.mail_utils import load_disposable_domains
from fastapi import BackgroundTasks
import uuid
from app.utils.cache import test_email_status_cache


router = APIRouter(prefix="/email", tags=["Email Validation Functions"])

DEFAULT_SENDER_EMAIL = "verify@example.com"
DISPOSABLE_DOMAINS = load_disposable_domains()


@router.post("/test_single_email", response_model=TestEmailWrapper)
async def create_single_email(
    test_email: SimpleEmailCheckRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    test_id = str(uuid.uuid4())
    test_email_status_cache[test_id] = {"status": "processing"}

    service = EmailService(db)
    background_tasks.add_task(service.create_test_email, user.user_Id, test_email, test_id)

    return TestEmailWrapper(
        message="Email test started. Check back shortly.",
        status=status.HTTP_202_ACCEPTED,
        test_id=test_id,
    )


@router.get("/test_single_email_status/{test_id}", response_model=TestEmailWrapper)
def get_test_email_status(test_id: str, db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    task = test_email_status_cache.get(test_id)
    if not task:
        raise HTTPException(status_code=404, detail="Test status not found")

    if task["status"] == "completed":
        email = db.query(TestEmail).filter(TestEmail.id == task["email_id"]).first()
        return TestEmailWrapper(
            message=task["message"],
            status=status.HTTP_200_OK,
            # test_id=test_id,
            data=email,
        )

    elif task["status"] == "failed":
        raise HTTPException(status_code=500, detail=task["error"])

    return TestEmailWrapper(message="Still working...", status=status.HTTP_202_ACCEPTED, test_id=test_id, data=None)


@router.get("/test_single_email/{test_email_id}", response_model=TestEmailResponseWrapper)
def get_single_test_email(test_email_id: int, db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    """
    Retrieve a single tested email by its ID.

    Args:

        email_id (int): ID of the tested email to retrieve.

    Returns:

        JSONResponse: The tested email data.

    Raises:

        HTTPException: If the email with given ID is not found.
    """
    service = EmailService(db)
    test_email = service.get_test_email(test_email_id, user.user_Id)

    return TestEmailResponseWrapper(
        message="Test email found successfully.", status=status.HTTP_302_FOUND, data=TestEmailResponse.model_validate(test_email)
    )


@router.get("/recent_tested_emails", response_model=AllTestEmaislOrderedByCreationTime)
async def get_all_recent_tested_emails(db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    """
    Get all tested emails ordered by creation time.

    Returns:

        JSONResponse: List of all tested emails.
    """
    """Get all tested emails ordered by creation time"""
    service = EmailService(db)
    test_emails = service.get_emails_by_creation_time(user.user_Id)
    return {
        "message": "Emails fetched successfully.",
        "status": status.HTTP_200_OK,
        "data": jsonable_encoder(test_emails),
    }


@router.get("/all_single_tested_emails", response_model=AllTestEmaislByUserId)
def get_all_single_tested_emails_by_user_id(db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    """
    Get all test emails for the current user.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of emails tested by the user.
    """
    """
    Get all test emails for the current user.
    """
    service = EmailService(db)
    test_emails = service.get_all_test_emails(user.user_Id)
    return {"message": "All test emails read successfully.", "status": status.HTTP_200_OK, "data": jsonable_encoder(test_emails)}


# Bulk Email Endpoints
@router.post("/test_bulk_emails_with_file_upload", summary="Upload a file (.csv or .txt) to create bulk email stats")
def upload_bulk_emails_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Upload a CSV or TXT file to test bulk emails and generate stats.

    Args:

        file (UploadFile): The uploaded CSV or TXT file containing emails.
        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: Summary of tested emails and stats.

    Raises:

        HTTPException: If file format is unsupported or processing fails.
    """
    service = EmailService(db)
    result = service.process_bulk_email_file(file, user.user_Id)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Bulk emails created successfully from file",
            "Status_Code": status.HTTP_201_CREATED,
            "data": result.dict(),
        },
    )


@router.post("/bulk_email_test_by_copy_paste", status_code=status.HTTP_201_CREATED)
def create_bulk_email_by_copy_paste(
    payload: BulkEmailStatsCreateWithEmails = Body(),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Test bulk emails by providing a list of emails directly (copy/paste).

    Args:

        emails (List[str]): List of email addresses to test.
        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: Result summary of tested emails.

    Raises:

        HTTPException: If input is invalid or testing fails.
    """
    service = EmailService(db)
    result = service.create_bulk_email_with_copy_paste(payload, user.user_Id)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Bulk emails created successfully from copy/paste",
            "Status_Code": status.HTTP_201_CREATED,
            "data": result.dict(),
        },
    )


@router.get("/all_tested_bulk_emails_group_by_files", response_model=AllTestEmailsByFileResponseWrapper)
def get_all_bulk_emails_grouped_by_files(
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    """
    Get all bulk tested emails grouped by uploaded files.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of grouped email test results.
    """

    service = EmailService(db)
    grouped_emails = service.get_all_emails_grouped_by_files(user.user_Id)

    return {
        "message": "Emails fetched successfully",
        "status": status.HTTP_200_OK,
        "data": [
            {
                "file_id": group["file_id"],
                "file_name": group["file_name"],
                "emails": [TestEmailResponse.model_validate(email) for email in group["emails"]],
            }
            for group in grouped_emails
        ],
    }


@router.get("/bulk_emails_file_stats/{file_id}", response_model=FileStatsResponseWrapper)
def get_file_stats_by_file_id(
    file_id: int,
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    """
    Get all bulk tested emails grouped by uploaded files.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of grouped email test results.
    """
    service = EmailService(db)
    stats = service.get_file_stats(file_id, user.user_Id)

    if not stats:
        raise HTTPException(status_code=404, detail="File not found or no emails present")

    return {
        "message": "File stats fetched successfully.",
        "status": status.HTTP_200_OK,
        "data": stats,
    }


@router.put("/filename_update")
async def update_filename(
    db: Session = Depends(get_db),
    file_id: int = Query(...),
    new_filename: str = Query(...),
    user: UserInfo = Depends(get_current_user),
):
    """
    Update the filename of an uploaded bulk email file.

    Args:

        file_id (int): ID of the file to rename.
        new_filename (str): New name for the file.
        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: Confirmation of the renamed file.

    Raises:

        HTTPException: If the file is not found or renaming fails.
    """
    service = EmailService(db)
    updated_filename = service.update_file_name_by_id(file_id, new_filename, user.user_Id)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "Message": "File name changed successfully.",
            "Status_Code": status.HTTP_202_ACCEPTED,
            "data": updated_filename,
        },
    )


@router.delete("/single_tested_email", response_model=TestEmailWrapper)
async def delete_single_tested_email(
    test_email_id: int = Query(...),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Soft delete a single tested email by its ID.

    Args:

        email_id (int): ID of the tested email to delete.

    Returns:

        JSONResponse: Confirmation of deletion.

    Raises:

        HTTPException: If the email is not found.
    """
    service = EmailService(db)
    deleted_email = service.soft_delete_test_email_by_id(test_email_id, user.user_Id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Test email deleted successfully.",
            "Status_Code": status.HTTP_200_OK,
            "data": deleted_email,
        },
    )


@router.delete("/bulk_emails_file_by_file_id")
async def delete_bulk_emails_file(
    file_id: int = Query(...),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Soft delete a bulk email file and all associated emails by file ID.

    Args:

        file_id (int): ID of the uploaded file.

    Returns:

        JSONResponse: Confirmation of deletion.

    Raises:

        HTTPException: If the file is not found.
    """
    service = EmailService(db)
    deleted_file = service.soft_delete_bulk_emails_file_by_id(file_id, user.user_Id)

    return {
        "message": "Bulk emails file have been deleted successfully.",
        "Status_Code": status.HTTP_200_OK,
        "data": BulkEmailStatsRead.model_validate(deleted_file),
    }


@router.get("/emails_for_csv/{file_id}", response_model=dowloadFileWrapper)
def get_emails_for_csv(
    file_id: int,
    include_risky: bool = Query(True),
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    """
    Get all emails from a file, optionally including risky ones, for CSV download.

    Args:

        file_id (int): ID of the uploaded file.
        include_risky (bool): Whether to include risky emails.

    Returns:

        StreamingResponse: CSV file with email data.

    Raises:

        HTTPException: If file is not found or data retrieval fails.
    """
    service = EmailService(db)
    emails = service.get_emails_for_csv(file_id, user.user_Id, include_risky)
    return {
        "message": "Emails fetched successfully.",
        "status": status.HTTP_200_OK,
        "data": [TestEmailResponse.model_validate(jsonable_encoder(email)) for email in emails],
    }


@router.get("/all_files_with_delieved_emails_and_status", response_model=FileStatsResponse)
def get_user_files(user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all uploaded files with their delivered email stats and status.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of uploaded files with statistics.
    """

    service = EmailService(db)
    files_data = service.get_all_files_with_delieved_emails_and_status(user.user_Id)
    return {"message": "Files fetched successfully.", "status": status.HTTP_200_OK, "data": files_data}
