from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from app.services.subscription_stripe import create_checkout_session, handle_webhook
from app.database.db_config import get_db
from app.schemas.subcription_stripe import CheckoutSessionRequest, UserInfo
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post("/create-checkout-session")
async def create_session(
    data: CheckoutSessionRequest, user: UserInfo = Depends(get_current_user)
):
    url = create_checkout_session(user.email, data.card_title, data.card_price)
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db=Depends(get_db)):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        result = handle_webhook(payload, sig_header, db)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
