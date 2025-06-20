from fastapi.responses import JSONResponse
from fastapi import status
from typing import Any, Optional

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