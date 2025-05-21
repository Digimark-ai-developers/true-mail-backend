from datetime import datetime
from typing import Annotated  # Optional

from fastapi import APIRouter, Depends  # HTTPException, status

# from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.db_config import get_db
from app.models.credits import CreditUsage
from app.models.user import User

# from app.schemas.credit import CreditBalanceResponseWrapper
from app.schemas.email import (  # CreditUsageBase,; TestEmailResponse,
    SimpleEmailCheckRequest,
    TestEmailBase,
    TestEmailResponseWrapper,
)
from app.utils.validator import check_email_reachability, load_disposable_domains

router = APIRouter()

DEFAULT_SENDER_EMAIL = "verify@example.com"
DISPOSABLE_DOMAINS = load_disposable_domains()


async def deduct_credits(db: Session, user_id: str, email: str) -> bool:
    """Deduct credits for email verification"""
    # Check if user has sufficient credits
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or user.remaining_credits < 1:
        return False

    # Deduct credit
    user.remaining_credits -= 1
    db.add(user)

    # Record credit usage
    credit_usage = CreditUsage(
        user_id=user_id, email_or_file_id=0, credits_used=1, created_at=datetime.utcnow()
    )  # 0 for single email verification
    db.add(credit_usage)
    db.commit()
    return True


@router.post("/quick-verify", response_model=TestEmailResponseWrapper)
async def quick_email_verify(
    db: Annotated[Session, Depends(get_db)], request: SimpleEmailCheckRequest, sender_email: str = DEFAULT_SENDER_EMAIL
):
    """
    Lightweight email verification without database storage or full WHOIS checks.
    Returns results in the standard schema format.
    """
    email = request.user_tested_email

    # Perform basic validation using core utils
    is_valid, message = check_email_reachability(
        email=email, sender_email=sender_email, disposable_domains=DISPOSABLE_DOMAINS
    )

    # Extract domain (basic parsing)
    domain = email.split("@")[-1] if "@" in email else ""

    # Build response according to TestEmailBase schema
    response_data = TestEmailBase(
        user_tested_email=email,
        domain=domain,
        is_valid=is_valid,
        is_deliverable=is_valid,  # Assuming valid=deliverable in quick check
        is_disposable=domain.lower() in DISPOSABLE_DOMAINS,
        status=message,
        score=100 if is_valid else 0,
        # Set other fields to None or defaults
        full_name=None,
        gender=None,
        reason=None if is_valid else message,
        is_free=False,
        is_risky=False,
        has_tag=False,
        alphabetical_characters=0,
        is_mailbox_full=False,
        has_role=False,
        is_accept_all=False,
        has_numerical_characters=0,
        has_unicode_symbols=0,
        has_no_reply=False,
        smtp_provider=None,
        mx_record=None,
        implicit_mx_record=None,
    )
    db.add(response_data)
    db.commit()
    db.refresh(response_data)

    return TestEmailResponseWrapper(message="Quick verification completed", status=200, data=response_data)
