# app\routes\email.py
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.schemas.auth import UserID
from app.schemas.email import (
    AllTestEmailsByFileResponseWrapper,
    AllTestEmaislByUserId,
    BulkEmailStatsCreateWithEmails,
    BulkEmailStatsRead,
    FileStatsResponse,
    FileStatsResponseWrapper,
    TestEmailBase,
    TestEmailResponse,
    TestEmailResponseWrapper,
    TestEmailWrapper,
    dowloadFileWrapper,
)
from app.schemas.user import UserInfo
from app.services.email_service import EmailService
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/email", tags=["Email Validation Functions"])


@router.post("/single_email", response_model=TestEmailWrapper)
async def create_single_email(
    test_email: TestEmailBase, db: Session = Depends(get_db), user: UserID = Depends(get_current_user)
):
    service = EmailService(db)
    email = await service.create_email(user.user_Id, test_email)

    return TestEmailWrapper(
        message="Email tested successfully.",
        status=status.HTTP_201_CREATED,
        data=TestEmailBase.model_validate(email),
    )


@router.get("/single_email/{test_email_id}", response_model=TestEmailResponseWrapper)
def get_single_test_email(test_email_id: int, db: Session = Depends(get_db)):
    service = EmailService(db)
    test_email = service.get_test_email(test_email_id)

    return TestEmailResponseWrapper(
        message="email found successfully.",
        status=status.HTTP_302_FOUND,
        data=TestEmailResponse.model_validate(test_email),
    )


@router.get("/all_single_emails", response_model=AllTestEmaislByUserId)
def get_all_single_emails_by_user_id(db: Session = Depends(get_db), user: UserID = Depends(get_current_user)):
    """
    Get all test emails for the current user.
    """
    service = EmailService(db)
    test_emails = service.get_all_emails(user.user_Id)  # type: ignore
    return {
        "message": "All test emails read successfully.",
        "status": status.HTTP_200_OK,
        "data": jsonable_encoder(test_emails),
    }


@router.post(
    "/bulk_email_stats_with_emails/upload",
    summary="Upload a file (.csv or .txt) to create bulk email stats",
)
async def upload_bulk_email_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    if file.filename.endswith(".csv"):
        try:
            contents = await file.read()
            file_content = contents.decode("utf-8")

            service = EmailService(db)

            # ✅ Use `user.id` instead of `user.user_id`
            result = await service.validate_emails_from_csv(user.user_Id, file_content, file.filename)

            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=jsonable_encoder(
                    {
                        "message": "Bulk emails created successfully from file",
                        "Status_Code": status.HTTP_201_CREATED,
                        "data": result,
                    }
                ),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="File type not supported. Please upload a CSV file.")

    # new route copy past


@router.post(
    "/copy_past_emails",
    summary="Validate multiple emails at once Copy / Past",
    response_model=BulkEmailStatsCreateWithEmails,
)
async def copy_past_emails(
    payload: BulkEmailStatsCreateWithEmails,
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    service = EmailService(db)
    result = await service.copy_past_emails(user_id=user.user_Id, emails=payload.test_emails)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(
            {
                "message": "Emails validated successfully",
                "Status_Code": status.HTTP_201_CREATED,
                "data": result,
            }
        ),
    )


@router.get("/allbulk_emails_group_by_files", response_model=AllTestEmailsByFileResponseWrapper)
def get_all_bulk_emails_grouped_by_files(
    db: Session = Depends(get_db),
    user: UserID = Depends(get_current_user),
):

    service = EmailService(db)
    grouped_emails = service.get_all_emails_grouped_by_files(user.user_Id)  # type: ignore

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
    service = EmailService(db)
    stats = service.get_file_stats(file_id, user.user_Id)  # type: ignore

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
    service = EmailService(db)
    updated_filename = service.update_file_name_by_id(file_id, new_filename, user.user_Id)  # type: ignore

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "Message": "File name changed successfully.",
            "Status_Code": status.HTTP_202_ACCEPTED,
            "data": updated_filename,
        },
    )


@router.delete("/single_tested_email", response_model=TestEmailWrapper)
async def delete_single_email(
    test_email_id: int = Query(...),
    db: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
):
    """Soft deletes test email by ID"""
    service = EmailService(db)
    deleted_email = service.soft_delete_email_by_id(test_email_id, user.user_Id)  # type: ignore

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
    """Soft delete bulk email stats by ID"""
    service = EmailService(db)
    deleted_file = service.soft_delete_bulk_emails_file_by_id(file_id, user.user_Id)  # type: ignore

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
    service = EmailService(db)
    emails = service.get_emails_for_csv(file_id, user.user_Id, include_risky)  # type: ignore
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
