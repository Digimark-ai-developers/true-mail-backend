from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.services.subscription_stripe import PaymentService
from app.database.db_config import get_db
from app.schemas.subcription_stripe import CheckoutSessionRequest, GetInvoicesWrapper, UserInfo
from app.utils.jwt_handler import get_current_user
from sqlalchemy.orm import Session
from app.schemas.auth import UserID


router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post("/create_checkout_session")
async def create_session(
    data: CheckoutSessionRequest,
    user: UserID = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe checkout session for purchasing credits.

    Args:

        data (CheckoutSessionRequest): Details of the subscription plan and credit amount.
        user (UserInfo): The currently authenticated user's information.

    Returns:

        dict: Contains a success message, status code, and the Stripe checkout URL.
    """
    service = PaymentService(db)
    checkout_url = service.create_checkout_session(user.email, data.success_url, data.card_price, data.credits, user.user_Id)  # success_url
    return {
        "message": "Stripe checkout session created successfully.",
        "status_code": status.HTTP_200_OK,
        "checkout_url": checkout_url,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming Stripe webhook events.

    Args:

        request (Request): Incoming HTTP request containing the webhook payload.

    Returns:

        JSONResponse: Response with the result of the webhook processing.

    Raises:

        HTTPException: If the webhook is invalid or processing fails.
    """
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


@router.get("/invoices", response_model=GetInvoicesWrapper)
async def get_invoices(user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve the Stripe invoice history for the current user.

    Args:

        user (UserInfo): The currently authenticated user's information.

    Returns:

        GetInvoicesWrapper: Contains a message, status code, and a list of invoices.
    """
    service = PaymentService(db)
    invoices = service.get_invoices(user.user_Id)
    return {"message": "Invoices fetched successfully.", "status_code": status.HTTP_200_OK, "data": invoices}
