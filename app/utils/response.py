from typing import Any, Optional, List
from fastapi.responses import JSONResponse
from fastapi import status
from app.models.validator import SingleValidation, FileValidation
from app.schemas.validator import EmailValidationData, GeneralInfo, Details, MailServerInformation


def success_response(message: str, data: Optional[Any] = None, status_code: int = status.HTTP_200_OK):
    return JSONResponse(
        content={
            "status_code": status_code,
            "message": message,
            "data": data,
        },
        status_code=status_code,
    )


def error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST, data: Optional[Any] = None):
    return JSONResponse(
        content={
            "status_code": status_code,
            "message": message,
            "data": data,
        },
        status_code=status_code,
    )


def single_email_validation_response(data: SingleValidation) -> EmailValidationData:
    return EmailValidationData(
        validated_email=data.validated_email,
        file_id=0,
        score=data.score,
        general=GeneralInfo(
            full_name=data.full_name,
            gender=data.gender,
            status=data.status,
            reason=data.reason,
            domain=data.domain,
        ),
        details=Details(
            is_free=data.is_free,
            has_role=data.has_role,
            disposable=data.disposable,
            accept_all=data.accept_all,
            has_tag=data.has_tag,
            numerical_characters=data.numerical_characters,
            alphabetical_characters=data.alphabetical_characters,
            unicode_symbols=data.unicode_symbols,
            is_mailbox_full=data.is_mailbox_full,
            is_no_reply=data.is_no_reply,
        ),
        mail_server_information=MailServerInformation(
            smtp_provider=data.smtp_provider,
            mx_record=data.mx_record,
            implicit_mx_record=data.implicit_mx_record,
        ),
    )
    