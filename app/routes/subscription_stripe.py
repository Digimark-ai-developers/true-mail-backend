from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.schemas.subcription_stripe import CheckoutSessionRequest, UserInfo
from app.services.subscription_stripe import PaymentService
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post("/create-checkout-session")
async def create_session(
    data: CheckoutSessionRequest,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)
    checkout_url = service.create_checkout_session(
        user.email, data.card_title, data.card_price, user.user_Id, data.credits
    )
    return {
        "message": "Stripe checkout session created successfully.",
        "status_code": status.HTTP_200_OK,
        "checkout_url": checkout_url,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        payment_service = PaymentService(db)
        result = payment_service.handle_webhook(payload, sig_header)

        return JSONResponse(
            status_code=result["status_code"],
            content={
                "message": result["message"],
                "success": result["success"],
            },
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
