from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
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
    BulkEmailResponseWrapper,
    BulkEmailStatsWrapper,
    BulkEmailUploadRequest,
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
from app.utils.cache import test_email_status_cache, bulk_email_status_cache, copy_paste_email_status_cache


router = APIRouter(prefix="/email", tags=["Email Validation Functions"])

DEFAULT_SENDER_EMAIL = "verify@example.com"
DISPOSABLE_DOMAINS = load_disposable_domains()


@router.post("/single_email", response_model=TestEmailWrapper)
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


@router.get("/single_email_status/{test_id}", response_model=TestEmailWrapper)
def get_test_email_status(test_id: str, db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    task = test_email_status_cache.get(test_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task status not found")

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


@router.get("/single_email/{test_email_id}", response_model=TestEmailResponseWrapper)
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


@router.get("/recent_emails", response_model=AllTestEmaislOrderedByCreationTime)
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


@router.get("/all_single_emails", response_model=AllTestEmaislByUserId)
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
@router.post("/bulk_email_stats_with_emails/upload")
async def upload_bulk_email_file_json(
    background_tasks: BackgroundTasks,
    request_data: BulkEmailUploadRequest,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if not request_data.file_name.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="File type not supported. Please upload a CSV or TXT file.")

    try:
        task_id = str(uuid.uuid4())

        bulk_email_status_cache[task_id] = {
            "status": "processing",
            "message": "Processing bulk email file...",
        }

        background_tasks.add_task(
            EmailService.process_bulk_email_upload,
            task_id,
            user.user_Id,
            request_data.file_content,
            request_data.file_name,
            db,
        )

        return {
            "message": "Bulk email file is being processed.",
            "status": 202,
            "task_id": task_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/bulk_email_status/{task_id}", response_model=BulkEmailResponseWrapper)
def get_bulk_email_status(task_id: str, user: UserID = Depends(get_current_user)):
    task = bulk_email_status_cache.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] == "completed":
        return {"status": 200, "message": task["message"], "task_id": task_id, "data": task["result"]}

    elif task["status"] == "failed":
        raise HTTPException(status_code=500, detail=task["error"])

    return {"status": 202, "message": "Still processing...", "task_id": task_id, "data": None}


@router.post(
    "/copy_paste_email",
    summary="Validate multiple emails from pasted input",
)
async def copy_paste_email_start(
    payload: BulkEmailStatsCreateWithEmails,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    task_id = str(uuid.uuid4())
    copy_paste_email_status_cache[task_id] = {"status": "processing"}

    service = EmailService(db)
    background_tasks.add_task(service.copy_paste_emails_background, user.user_Id, payload.test_emails, task_id,payload.file_name)

    return BulkEmailStatsWrapper(message="Email validation started. Check back shortly.", status=status.HTTP_202_ACCEPTED, task_id=task_id, data=None)


@router.get(
    "/copy_paste_email_status/{task_id}",
    summary="Check status of pasted email validation",
    response_model=BulkEmailStatsWrapper,
)
def get_copy_paste_email_status(
    task_id: str,
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):
    # First check the cache for task status
    task = copy_paste_email_status_cache.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Validation status not found")

    # If task is still processing, return immediately
    if task["status"] == "processing":
        return BulkEmailStatsWrapper(
            message="Still processing...",
            status=status.HTTP_202_ACCEPTED,
            task_id=task_id,
            data=None,
        )

    # If task failed, return error
    if task["status"] == "failed":
        raise HTTPException(status_code=500, detail=task["error"])

    # If completed, return cached data
    if task["status"] == "completed":
        try:
            return BulkEmailStatsWrapper(
                message=task["message"],
                status=status.HTTP_200_OK,
                task_id=task_id,
                data=task["data"].model_dump() if hasattr(task["data"], 'model_dump') else task["data"],
            )
        except Exception as e:
            # If there's an error processing the completed data, return error
            raise HTTPException(status_code=500, detail=f"Error processing completed data: {str(e)}")

    # Fallback response for unexpected status
    return BulkEmailStatsWrapper(
        message="Unknown status",
        status=status.HTTP_202_ACCEPTED,
        task_id=task_id,
        data=None,
    )


@router.get("/all_bulk_emails_group_by_files", response_model=AllTestEmailsByFileResponseWrapper)
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


@router.delete("/single_email", response_model=TestEmailWrapper)
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
def download_emails_for_csv(
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
