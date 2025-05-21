# from app.middlewares.auth_middleware import get_current_user

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.schemas.auth import UserID
from app.schemas.credit import (
    CreditBalanceResponseWrapper,
    CreditHistoryResponseWrapper,
    CreditUsageResponse,
    CreditUsageResponseWrapper,
)
from app.services.credit_service import CreditService
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance", summary="Get current credit balance", response_model=CreditBalanceResponseWrapper)
def get_credit_balance(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CreditService(db)
    credit_data = service.fetch_credit_balance(user.user_Id)
    return CreditBalanceResponseWrapper(
        message="Credit balance read successfully", status=status.HTTP_200_OK, data=credit_data
    )


@router.get("/usage", summary="Get all credit usage for user", response_model=CreditUsageResponseWrapper)
def get_credit_usage(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CreditService(db)
    usage_data = service.fetch_credit_usage(user.user_Id)
    usage_data_dict = [CreditUsageResponse.model_validate(item) for item in usage_data]
    return CreditUsageResponseWrapper(
        message="Credit usage found successfully", status=status.HTTP_200_OK, data=usage_data_dict
    )


@router.get("/history", summary="Get credit purchase history", response_model=CreditHistoryResponseWrapper)
def get_credit_history(user: UserID = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CreditService(db)
    history_data = service.fetch_credit_history(user.user_Id)
    return CreditHistoryResponseWrapper(
        message="Credit purchase history found successfully", status=status.HTTP_200_OK, data=history_data
    )
