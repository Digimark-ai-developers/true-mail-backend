import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import TypeAdapter
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.validator import SingleValidation
from app.schemas.validator import FileValidationEmailsCreate, FileData, FileStatsSchema
from app.dependencies.auth import get_current_user, UserInfo
from app.utils.response import success_response, single_email_validation_response
from app.services.validator import EmailValidationService
from app.utils.cache import single_email_validation_status_cache, copy_paste_email_validation_status_cache
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


# Single email validation routes
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


@router.delete("/delete_single_validated_email", response_model=success_response)
async def delete_single_validated_email(
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
    service = EmailValidationService(db)
    deleted_email = service.soft_delete_validated_email_by_id(test_email_id, user.user_id)

    return success_response(
        message="Test email deleted successfully.",
        status_code=status.HTTP_200_OK,
        data=[
            single_email_validation_response(deleted_email).model_dump(),
            {
                "Deleted": "Validated email deleted.",
            },
        ],
    )


# File email validation routes
@router.post(
    "/validate_copy_pasted_emails",
    summary="Validate multiple emails from pasted input",
    response_model=success_response,
)
async def copy_paste_email_start(
    payload: FileValidationEmailsCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    task_id = str(uuid.uuid4())
    copy_paste_email_validation_status_cache[task_id] = {"status": "processing"}
    if payload.file_name == "" or payload.file_name == None:
        payload.file_name = "Copy/Paste"

    service = EmailValidationService(db)
    background_tasks.add_task(
        service.copy_paste_emails_background,
        user_id=user.user_id,
        emails=payload.validate_emails,
        task_id=task_id,
        file_name=payload.file_name,
    )

    return success_response(
        message="Email validation started. Check back shortly.",
        status_code=status.HTTP_202_ACCEPTED,
        data=task_id,
    )


@router.get(
    "/copy_paste_email_status/{task_id}",
    summary="Check status of pasted emails validation",
    response_model=success_response,
)
def get_copy_paste_email_status(
    task_id: str,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    task = copy_paste_email_validation_status_cache.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Validation status not found")

    if task["status"] == "completed":
        return success_response(
            message=task["message"],
            status_code=status.HTTP_200_OK,
            data=task["data"].model_dump(),  # ✅ convert to dict
        )

    elif task["status"] == "failed":
        raise HTTPException(status_code=500, detail=task["error"])

    return success_response(
        message="Still working...",
        status_code=status.HTTP_202_ACCEPTED,
        data=task_id,
    )


@router.get("/all_file_validated_emails_grouped_by_files")
def get_all_bulk_emails_grouped_by_files(
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get all bulk tested emails grouped by uploaded files.

    Args:
        current_user (User): The currently authenticated user.

    Returns:
        JSONResponse: List of grouped email test results.
    """
    service = EmailValidationService(db)
    grouped_emails = service.get_all_emails_grouped_by_files(user.user_id)

    # Build the raw data structure for each file group
    raw_data = [
        {
            "file_id": group["file_id"],
            "file_name": group["file_name"],
            "file_status": group["file_status"],
            "graph": group["graph"],
            "emails": [single_email_validation_response(email).model_dump() for email in group["emails"]],
        }
        for group in grouped_emails
    ]

    # ✅ Validate against FileData schema list
    validated_data = TypeAdapter(list[FileData]).validate_python(raw_data)
    data_as_dicts = [item.model_dump() for item in validated_data]

    return success_response(
        message="Emails fetched successfully",
        status_code=status.HTTP_200_OK,
        data=data_as_dicts,
    )


@router.get("/file_emails_file_stats/{file_id}")
def get_file_stats_by_file_id(
    file_id: int,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """
    Get all bulk tested emails grouped by uploaded files.
    """
    service = EmailValidationService(db)
    stats = service.get_file_stats(file_id, user.user_id)

    if not stats:
        raise HTTPException(status_code=404, detail="File not found or no emails present")

    # ✅ validate structure
    validated_stats = TypeAdapter(FileStatsSchema).validate_python(stats)

    return success_response(
        message="File stats fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=validated_stats.model_dump(mode="json"),
    )


@router.put("/update-file-name/{file_id}")
async def update_filename(
    db: Session = Depends(get_db),
    file_id: int = str,
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
    service = EmailValidationService(db)
    updated_filename = service.update_file_name_by_id(file_id, new_filename, user.user_id)

    return success_response(
        message="File name changed successfully.",
        status_code=status.HTTP_202_ACCEPTED,
        data=updated_filename,
    )


@router.delete("/delete_file_by_file_id")
async def delete_file_by_file_id(
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
    service = EmailValidationService(db)
    deleted_file = service.soft_delete_file_by_file_id(file_id, user.user_id)

    return success_response(
        message="Bulk emails file have been deleted successfully.",
        status_code=status.HTTP_200_OK,
        data=deleted_file.model_dump(),
    )


@router.get("/emails_for_csv/{file_id}", response_model=success_response)
def download_emails_for_csv(
    file_id: int,
    include_risky: bool = Query(True),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
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

    service = EmailValidationService(db)
    emails = service.get_emails_for_csv(file_id, user.user_id, include_risky)
    return success_response(
        message= "Emails fetched successfully.",
        status_code= status.HTTP_200_OK,
        data= [(jsonable_encoder(email)) for email in emails],
    )


@router.get("/all_files_with_delieved_emails_and_status", response_model=success_response)
def get_user_files(user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all uploaded files with their delivered email stats and status.

    Args:

        current_user (User): The currently authenticated user.

    Returns:

        JSONResponse: List of uploaded files with statistics.
    """

    service = EmailValidationService(db)
    files_data = service.get_all_files_with_delieved_emails_and_status(user.user_id)
    return success_response(message="Files fetched successfully.", status_code=status.HTTP_200_OK, data=files_data)
