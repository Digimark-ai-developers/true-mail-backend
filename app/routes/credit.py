# from app.middlewares.auth_middleware import get_current_user
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.models.credits import Credit, CreditHistory, CreditUsage
from app.schemas.user import UserInfo

router = APIRouter(prefix="/credits", tags=["Credits"])


# @router.post("/use/{user_id}", summary="Use 1 credit for email validation")
# def use_credit(user_id: str, db: Session = Depends(get_db)):
#     credit = db.query(Credit).filter(Credit.user_id == user_id).first()
#     if not credit or credit.remaining_credits < 1:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Insufficient credits"
#         )

#     credit.remaining_credits -= 1
#     credit.total_credits -= 1
#     credit.last_updated = datetime.utcnow()

#     credit_usage = CreditUsage(
#         user_id=user_id,
#         email_or_file_id=0,  # You can link to email ID if available
#         quantity_used=1,
#         credits_used=Decimal("1.00"),
#         created_at=datetime.utcnow()
#     )

#     db.add(credit)
#     db.add(credit_usage)
#     db.commit()

#     return {"message": "Credit used successfully"}


@router.get("/usage/{user_id}", summary="Get all credit usage for user")
def get_credit_usage(user_id: str, db: Session = Depends(get_db)):
    usage = db.query(CreditUsage).filter(CreditUsage.user_id == user_id).all()
    usage_dict = jsonable_encoder(usage)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND, content={"message": "Credit usage found successfully.", "data": usage_dict}
    )


@router.get("/history/{user_id}", summary="Get credit purchase history")
def get_credit_history(user_id: str, db: Session = Depends(get_db)):
    history = db.query(CreditHistory).filter(CreditHistory.user_id == user_id).all()
    history_dict = jsonable_encoder(history)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND,
        content={"message": "Credit history found successfully.", "data": history_dict},
    )


@router.get("/balance/{user_id}", summary="Get current credit balance")
def get_credit_balance(user_id: str, db: Session = Depends(get_db)):
    credit = db.query(Credit).filter(Credit.user_id == user_id).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    credit_dict = jsonable_encoder(credit)
    return JSONResponse(
        status_code=status.HTTP_302_FOUND,
        content={"message": "Credit Balance found successfully.", "data": credit_dict},
    )
