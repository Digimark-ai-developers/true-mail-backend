from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, UserInfo
from app.schemas.subscription_stripe import CheckoutSessionRequest, GetInvoices
from app.services.subscription_stripe import PaymentService
from app.utils.response import success_response, error_response

router = APIRouter()


@router.post("/create_checkout_session")
async def create_session(
    data: CheckoutSessionRequest,
    user: UserInfo = Depends(get_current_user),
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
    checkout_url = service.create_checkout_session(
        user.email, data.success_url, data.card_price, data.credits, user.user_id
    )  # success_url
    return success_response(
        message="Stripe checkout session created successfully.",
        status_code=status.HTTP_200_OK,
        data={
            "checkout_url": checkout_url,
        },
    )


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
        print("random")
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        payment_service = PaymentService(db)
        result = payment_service.handle_webhook(payload, sig_header)

        return success_response(
            message=f"{result['message']}",
            status_code=result["status_code"],
            data={
                "success": result["success"],
            },
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        return error_response(message=f"{str(e)}", data=None)


@router.get("/invoices", response_model=success_response)
async def get_invoices(user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve the Stripe invoice history for the current user.

    Args:

        user (UserInfo): The currently authenticated user's information.

    Returns:

        GetInvoicesWrapper: Contains a message, status code, and a list of invoices.
    """
    service = PaymentService(db)
    invoices = service.get_invoices(user.user_id)
    return success_response(
        message="Invoices fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=[jsonable_encoder(item) for item in invoices],
    )
