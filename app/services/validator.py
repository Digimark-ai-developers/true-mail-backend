import asyncio
import csv
import re
from datetime import datetime, timezone
from io import StringIO
from typing import List

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.validator import SingleValidation, FileValidation
from app.models.user import User
from app.utils.cache import file_emails_validation_status_cache
from app.utils.cache import copy_paste_email_validation_status_cache as cache
from app.utils.cache import single_email_validation_status_cache
from app.utils.validator import (
    evaluate_email_score_and_risk,
    get_mx_record,
    get_smtp_provider,
    load_disposable_domains,
    perform_email_checks,
    validate_email_syntax,
)


class EmailValidationService:
    def __init__(self, db: Session):
        self.db = db

    async def homepage_email_validation(self, email: str, sender_email: str):
        disposable_domains = load_disposable_domains()
        is_syntax_valid = validate_email_syntax(email)
        mx_record_result = get_mx_record(email)
        mx_record = mx_record_result[0] if mx_record_result else None
        implicit_mx = mx_record_result[1] if mx_record_result and len(mx_record_result) > 1 else None

        smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
            target_email=email, sender_email=sender_email, disposable_domains=disposable_domains
        )

        return "Deliverable" if is_syntax_valid and smtp_deliverable else "Undeliverable"

    async def create_email_validation(self, user_id: int, email: str, test_id: str):
        try:
            # Validate User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=400, detail="User ID not found")

            # Sender Mail
            sender_email = user.email

            # Deduct credits
            credit = self.db.query(User).filter(User.id == user_id).first()
            if credit.remaining_credits < 1:
                raise HTTPException(status_code=403, detail="Insufficient credits to test email")

            credit.remaining_credits -= 1
            credit.updated_at = datetime.now(timezone.utc)
            self.db.add(credit)

            # Validate email
            target_email = email
            if not target_email:
                raise HTTPException(status_code=400, detail="No email provided to validate.")

            disposable_domains = load_disposable_domains()
            is_syntax_valid = validate_email_syntax(target_email)
            mx_record_result = get_mx_record(target_email)
            mx_record = mx_record_result[0] if mx_record_result else None
            implicit_mx = mx_record_result[1] if mx_record_result and len(mx_record_result) > 1 else None

            smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
                target_email=target_email, sender_email=sender_email, disposable_domains=disposable_domains
            )

            email_domain = target_email.split("@", 1)[-1].lower()
            is_disposable = int(email_domain in disposable_domains)

            match = re.search(r"@([a-zA-Z0-9.-]+)", target_email)
            domain_name = match.group(1) if match else None

            local_part = re.sub(r"[^a-zA-Z._-]", "", target_email.split("@", 1)[0])
            cleaned_name = re.sub(r"[\\._-]+", " ", local_part).strip()
            full_name = " ".join(part.capitalize() for part in cleaned_name.split())

            email_str = target_email.lower()
            alphabetical_count = sum(c.isalpha() for c in email_str)
            numerical_count = sum(c.isdigit() for c in email_str)
            unicode_symbol_count = len(email_str) - alphabetical_count - numerical_count

            has_role = any(role in email_str for role in ["admin", "info", "support", "sales", "contact"])
            is_accept_all = "accept" in email_str or "all" in email_str
            has_no_reply = "no-reply" in email_str or "noreply" in email_str

            try:
                _, domain = target_email.split("@")
            except ValueError:
                domain = ""

            smtp_provider = get_smtp_provider(domain)

            score, is_risky, tags = evaluate_email_score_and_risk(
                is_syntax_valid=is_syntax_valid,
                smtp_deliverable=smtp_deliverable,
                is_disposable=bool(is_disposable),
                has_role=has_role,
                is_accept_all=is_accept_all,
                has_no_reply=has_no_reply,
                domain=email_domain,
                mx_record=mx_record,
                smtp_provider=smtp_provider,
            )

            email_data = SingleValidation(
                user_id=user_id,
                validated_email=email,
                file_id=0,
                score=score,
                # General
                full_name=full_name or "N/A",
                gender="N/A",
                status="Deliverable" if is_syntax_valid and smtp_deliverable else "Undeliverable",
                reason=validation_reason or smtp_reason,
                domain=domain_name,
                # Checks for deliverable
                is_deliverable=smtp_deliverable,
                is_risky=is_risky,
                is_valid=is_syntax_valid and smtp_deliverable,
                # Details
                is_free=True,
                has_role=has_role,
                disposable=is_disposable,
                accept_all=is_accept_all,
                has_tag=False,
                numerical_characters=numerical_count,
                alphabetical_characters=alphabetical_count,
                unicode_symbols=unicode_symbol_count,
                is_no_reply=has_no_reply,
                is_mailbox_full=False,
                # Mail Server Information
                smtp_provider=smtp_provider,
                mx_record=mx_record or "",
                implicit_mx_record=implicit_mx,
                # Backend usage
                soft_delete=False,
                created_at=datetime.now(timezone.utc),
            )

            self.db.add(email_data)
            self.db.commit()
            self.db.refresh(email_data)

            # Mark task as completed
            single_email_validation_status_cache[test_id] = {
                "status": "completed",
                "email_id": email_data.id,
                "message": "Test completed",
            }

        except Exception as e:
            self.db.rollback()
            single_email_validation_status_cache[test_id] = {
                "status": "failed",
                "error": str(e),
            }
            raise

    def get_test_email(self, validated_email_id: int, user_id: str):
        db_validated_email = (
            self.db.query(SingleValidation)
            .filter(
                SingleValidation.id == validated_email_id,
                SingleValidation.user_id == user_id,
                or_(SingleValidation.soft_delete.is_(False), SingleValidation.soft_delete.is_(None)),
            )
            .first()
        )
        if not db_validated_email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test email not found")

        return db_validated_email

    def get_emails_by_creation_time(self, user_id: str):
        query = (
            self.db.query(SingleValidation)
            .filter(SingleValidation.user_id == user_id, SingleValidation.soft_delete.is_(False))
            .order_by(SingleValidation.created_at.desc())
            .limit(5)
        )
        return query.all()

    def get_all_test_emails(self, user_id: str) -> List[SingleValidation]:
        return (
            self.db.query(SingleValidation)
            .filter(SingleValidation.user_id == user_id)
            .filter(or_(SingleValidation.soft_delete.is_(None), SingleValidation.soft_delete.is_(False)))
            .all()
        )
