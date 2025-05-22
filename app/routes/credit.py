# from app.middlewares.auth_middleware import get_current_user

from fastapi import APIRouter, Depends, status
from app.schemas.auth import UserID
from app.services.credit_service import CreditService
from sqlalchemy.orm import Session
from app.database.db_config import get_db
from app.utils.jwt_handler import get_current_user
from app.schemas.credit import (
    CreditBalanceResponseWrapper,
    CreditHistoryResponseWrapper,
    CreditUsageResponseWrapper,
)


router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance", summary="Get current credit balance", response_model=CreditBalanceResponseWrapper)
def get_credit_balance(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve the current credit balance for the authenticated user.

    Args:

        user (UserID): The authenticated user's ID extracted from the JWT token.

    Returns:

        CreditBalanceResponseWrapper: Wrapped response containing current credit balance.

    Example:

        {
            "status": 200,
            "message": "Credit balance read successfully",
            "data": {
                "total_credits": 1000,
                "used_credits": 150,
                "remaining_credits": 850
            }
        }
    """
    service = CreditService(db)
    credit_data = service.fetch_credit_balance(user.user_Id)
    return CreditBalanceResponseWrapper(message="Credit balance read successfully", status=status.HTTP_200_OK, data=credit_data)


@router.get("/usage", summary="Get all credit usage for user", response_model=CreditUsageResponseWrapper)
def get_credit_usage(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Fetch the complete credit usage records for the authenticated user.

    Args:

        user (UserID): The authenticated user's ID extracted from the JWT token.

    Returns:

        CreditUsageResponseWrapper: Wrapped response containing credit usage history.

    Example:

        {
            "status": 200,
            "message": "Credit usage found successfully",
            "data": [
                {
                    "usage_id": 1,
                    "credits_used": 5,
                    "activity": "Single email validation",
                    "timestamp": "2025-05-21T14:32:00"
                },
                {
                    "usage_id": 2,
                    "credits_used": 100,
                    "activity": "Bulk email file upload",
                    "timestamp": "2025-05-20T10:15:42"
                }
            ]
        }
    """
    service = CreditService(db)
    usage_data = service.fetch_credit_usage(user.user_Id)
    return CreditUsageResponseWrapper(message="Credit usage found successfully", status=status.HTTP_200_OK, data=usage_data)


@router.get("/history", summary="Get credit purchase history", response_model=CreditHistoryResponseWrapper)
def get_credit_history(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve the credit purchase history for the authenticated user.

    Args:

        user (UserID): The authenticated user's ID extracted from the JWT token.

    Returns:

        CreditHistoryResponseWrapper: Wrapped response containing list of credit purchases.

    Example:

         {
            "status": 200,
            "message": "Credit purchase history found successfully",
            "data": [
                {
                    "purchase_id": 1,
                    "credits_added": 1000,
                    "method": "Stripe",
                    "timestamp": "2025-05-19T08:45:00"
                },
                {
                    "purchase_id": 2,
                    "credits_added": 500,
                    "method": "PayPal",
                    "timestamp": "2025-05-10T16:23:11"
                }
            ]
        }
    """
    service = CreditService(db)
    history_data = service.fetch_credit_history(user.user_Id)
    return CreditHistoryResponseWrapper(message="Credit purchase history found successfully", status=status.HTTP_200_OK, data=history_data)
