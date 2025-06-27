import re
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional, Union

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.validator import SingleValidation, FileValidation
from app.models.user import User
from app.schemas.validator import FileEmailValidationData, FileDeletion
from app.utils.response import single_email_validation_response, error_response
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

    # Homepage email validation function
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

    # Single email validation function's
    async def create_email_validation(self, user_id: int, email: str, test_id: str):
        try:
            # Validate User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return error_response(message="User ID not found", data=None)

            # Sender Mail
            sender_email = user.email

            # Deduct credits
            credit = self.db.query(User).filter(User.id == user_id).first()
            if credit.remaining_credits < 1:
                return error_response(
                    message="Insuffucuent credits to validate email", status_code=status.HTTP_403_FORBIDDEN, data=None
                )

            credit.remaining_credits -= 1
            credit.updated_at = datetime.now(timezone.utc)
            self.db.add(credit)

            # Validate email
            target_email = email
            if not target_email:
                return error_response(message="No email provided to validate", data=None)

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
            return error_response(message=str(e), data=None)

    def get_test_email(self, validated_email_id: int, user_id: int):
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
            return error_response(message="Validated email not found", status_code=status.HTTP_404_NOT_FOUND, data=None)

        return db_validated_email

    def get_emails_by_creation_time(self, user_id: int):
        query = (
            self.db.query(SingleValidation)
            .filter(SingleValidation.user_id == user_id, SingleValidation.soft_delete.is_(False))
            .order_by(SingleValidation.created_at.desc())
            .limit(5)
        )
        return query.all()

    def get_all_test_emails(self, user_id: int) -> List[SingleValidation]:
        return (
            self.db.query(SingleValidation)
            .filter(SingleValidation.user_id == user_id)
            .filter(or_(SingleValidation.soft_delete.is_(None), SingleValidation.soft_delete.is_(False)))
            .all()
        )

    def soft_delete_validated_email_by_id(self, test_email_id: int, user_id: int):
        db_test_email = (
            self.db.query(SingleValidation)
            .filter(
                SingleValidation.id == test_email_id,
                SingleValidation.user_id == user_id,
                or_(SingleValidation.file_id == 0, SingleValidation.file_id.is_(None)),
                or_(
                    SingleValidation.soft_delete.is_(False),
                    SingleValidation.soft_delete.is_(None),
                    SingleValidation.soft_delete == 0,
                ),
            )
            .first()
        )
        print(db_test_email)

        if not db_test_email:
            return error_response(
                message="Validated email not found.", status_code=status.HTTP_404_NOT_FOUND, data=None
            )

        db_test_email.soft_delete = True
        self.db.commit()
        self.db.refresh(db_test_email)

        return db_test_email

    # File email validation function's
    def get_all_emails_grouped_by_files(self, user_id: int):
        validated_files = (
            self.db.query(FileValidation)
            .filter(
                FileValidation.user_id == user_id,
                or_(
                    FileValidation.soft_delete.is_(False),
                    FileValidation.soft_delete.is_(None),
                ),
            )
            .all()
        )

        results = []

        for bulk_file in validated_files:
            validated_emails = (
                self.db.query(SingleValidation)
                .filter(
                    SingleValidation.user_id == user_id,
                    SingleValidation.file_id == bulk_file.id,
                    or_(
                        SingleValidation.soft_delete.is_(False),
                        SingleValidation.soft_delete.is_(None),
                    ),
                )
                .all()
            )

            # Count statuses
            status_counts = Counter(email.status for email in validated_emails)

            # Construct the graph (status-wise count with hardcoded fill colors)
            graph = [
                {
                    "status": "Deliverable",
                    "total": status_counts.get("deliverable", bulk_file.deliverable),
                    "fill": "var(--color-deliverable)",
                },
                {
                    "status": "Undeliverable",
                    "total": status_counts.get("undeliverable", bulk_file.undeliverable),
                    "fill": "var(--color-undeliverable)",
                },
                {"status": "Risky", "total": status_counts.get("risky", bulk_file.risky), "fill": "var(--color-risky)"},
                {
                    "status": "Duplicate",
                    "total": status_counts.get("duplicate", bulk_file.duplicate_email),
                    "fill": "var(--color-Duplicate)",
                },
            ]

            results.append(
                {
                    "file_id": bulk_file.id,
                    "file_name": bulk_file.file_name,
                    "file_status": bulk_file.status or "processing",
                    "graph": graph,
                    "emails": validated_emails,  # Include this so the route can reuse it
                }
            )

        return results

    def get_file_stats(self, file_id: int, user_id: int):
        bulk_email = (
            self.db.query(FileValidation)
            .filter(
                FileValidation.id == file_id,
                FileValidation.user_id == user_id,
                FileValidation.soft_delete.is_(False),
            )
            .first()
        )

        if not bulk_email or bulk_email.total == 0:
            return None

        deliverable_emails = [
            {"status": "deliverable", "emails": bulk_email.deliverable, "fill": "var(--color-deliverable)"},
            {"status": "undeliverable", "emails": bulk_email.undeliverable, "fill": "var(--color-undeliverable)"},
            {"status": "risky", "emails": bulk_email.risky, "fill": "var(--color-risky)"},
            {"status": "duplicate", "emails": bulk_email.duplicate_email, "fill": "var(--color-duplicate)"},
        ]

        conversion_graph = deliverable_emails

        # Fetch only non-deleted emails
        validated_emails = (
            self.db.query(SingleValidation)
            .filter(
                SingleValidation.file_id == file_id,
                SingleValidation.user_id == user_id,
                SingleValidation.soft_delete.is_(False),
            )
            .all()
        )

        emails_list = [
            {
                "email_id": email.id,
                "email": email.validated_email,
                "reason": email.reason,
                "score": email.score,
                "status": "deliverable" if email.is_deliverable else "undeliverable",
            }
            for email in validated_emails
        ]

        return {
            "id": bulk_email.id,
            "file_name": bulk_email.file_name,
            "total": bulk_email.total,
            "duplicates": bulk_email.duplicate_email,
            "deliverable": bulk_email.deliverable,
            "undeliverable": bulk_email.undeliverable,
            "risky": bulk_email.risky,
            "status": bulk_email.status,
            "duplicated_percentage": round((bulk_email.duplicate_email / bulk_email.total) * 100, 2),
            "deliverable_percentage": round((bulk_email.deliverable / bulk_email.total) * 100, 2),
            "undeliverable_percentage": round((bulk_email.undeliverable / bulk_email.total) * 100, 2),
            "risky_percentage": round((bulk_email.risky / bulk_email.total) * 100, 2),
            "uploaded_at": bulk_email.created_at,
            "deliverable_emails": deliverable_emails,
            "conversion_graph": conversion_graph,
            "emails": emails_list,
        }

    async def copy_paste_emails_background(
        self,
        user_id: int,
        emails: List[str],
        task_id: str,
        file_name: Optional[str] = None,
    ):
        try:
            result = await self.copy_past_emails(user_id=user_id, emails=emails, file_name=file_name)
            bulk_email = (
                self.db.query(FileValidation)
                .filter(FileValidation.id == result.file_id, FileValidation.user_id == user_id)
                .first()
            )
            bulk_email.status = "Completed"
            self.db.commit()

            cache[task_id] = {
                "status": "completed",
                "message": "Emails validated successfully",
                "data": result,
            }
        except Exception as e:
            cache[task_id] = {
                "status": "failed",
                "error": str(e),
            }

    async def copy_past_emails(
        self,
        user_id: int,
        emails: List[str],
        sender_email: str = "test@example.com",
        file_name: Optional[str] = None,
    ) -> Union[FileEmailValidationData, JSONResponse]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return error_response(message="User ID not found.", data=None)

        credit = self.db.query(User).filter(User.id == user_id).first()
        if credit.remaining_credits < 1:
            return error_response(message="Insuffucuent credits to validate emails", status_code=403, data=None)

        disposable_domains = load_disposable_domains()

        # Clean and filter emails
        cleaned_emails = [email.strip().lower() for email in emails if email.strip() and validate_email_syntax(email)]

        if not cleaned_emails:
            return error_response(message="No valid emails found", data=None)

        total_emails = len(cleaned_emails)
        unique_emails = set(cleaned_emails)
        duplicate_count = total_emails - len(unique_emails)

        if credit.remaining_credits < len(cleaned_emails):
            return error_response(message="Insufficient credits", status_code=403, data=None)

        now = datetime.now(timezone.utc)
        bulk_stat = FileValidation(
            user_id=user_id,
            file_name=file_name,  # Using a default filename
            duplicate_email=duplicate_count,
            total_valid_emails=0,
            deliverable=0,
            risky=0,
            status="In-Progress",
            total=total_emails,
            created_at=now,
            soft_delete=False,
        )
        try:
            self.db.add(bulk_stat)
            self.db.flush()
            self.db.commit()

            bulk_id = bulk_stat.id
        except Exception as e:  # noqa: F841
            return error_response(message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, data=None)

        total_valid = 0
        risky_count = 0
        deliverable_count = 0
        undeliverable_count = 0

        test_email_objs = []

        for email in cleaned_emails:
            is_syntax_valid = validate_email_syntax(email)
            mx_record_result = get_mx_record(email)
            mx_record = mx_record_result[0] if mx_record_result else None
            implicit_mx = mx_record_result[1] if mx_record_result and len(mx_record_result) > 1 else None

            smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
                target_email=email, sender_email=sender_email, disposable_domains=disposable_domains
            )

            domain = email.split("@", 1)[-1].lower()
            is_disposable = int(domain in disposable_domains)

            match = re.search(r"@([a-zA-Z0-9.-]+)", email)
            domain_name = match.group(1) if match else "unknown"

            local_part = re.sub(r"[^a-zA-Z._-]", "", email.split("@", 1)[0])
            cleaned_name = re.sub(r"[\\._-]+", " ", local_part).strip()
            full_name = " ".join(part.capitalize() for part in cleaned_name.split()) or "N/A"

            alphabetical_count = sum(c.isalpha() for c in email)
            numerical_count = sum(c.isdigit() for c in email)
            unicode_symbol_count = len(email) - alphabetical_count - numerical_count

            has_role = any(role in email for role in ["admin", "info", "support", "sales", "contact"])
            is_accept_all = "accept" in email or "all" in email
            has_no_reply = "no-reply" in email or "noreply" in email

            smtp_provider = get_smtp_provider(domain)

            score, is_risky, tags = evaluate_email_score_and_risk(
                is_syntax_valid=is_syntax_valid,
                smtp_deliverable=smtp_deliverable,
                is_disposable=bool(is_disposable),
                has_role=has_role,
                is_accept_all=is_accept_all,
                has_no_reply=has_no_reply,
                domain=domain,
                mx_record=mx_record,
                smtp_provider=smtp_provider,
            )

            is_email_valid = is_syntax_valid and smtp_deliverable
            status = "valid" if is_email_valid else "invalid"

            if is_email_valid:
                total_valid += 1
                deliverable_count += 1
            if is_risky:
                risky_count += 1

            test_email_obj = SingleValidation(
                user_id=user_id,
                validated_email=email,
                file_id=0,
                score=score,
                # General
                full_name=full_name or "N/A",
                gender="N/A",
                status="Deliverable" if is_email_valid and smtp_deliverable else "Undeliverable",
                reason=validation_reason or smtp_reason,
                domain=domain_name,
                # Checks for deliverable
                is_deliverable=smtp_deliverable,
                is_risky=is_risky,
                is_valid=is_email_valid,
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
            if test_email_obj.status == "Undeliverable":
                undeliverable_count += 1
            test_email_objs.append(test_email_obj)

        bulk_email = (
            self.db.query(FileValidation)
            .filter(FileValidation.id == bulk_id, FileValidation.user_id == user_id)
            .first()
        )
        bulk_email.total_valid_emails = total_valid
        bulk_email.deliverable = deliverable_count
        bulk_email.undeliverable = undeliverable_count
        bulk_email.risky = risky_count
        self.db.commit()

        for test_email in test_email_objs:
            test_email.file_id = bulk_stat.id
            self.db.add(test_email)

        credit.remaining_credits -= total_emails
        credit.updated_at = now
        self.db.add(credit)

        try:
            self.db.commit()
            return FileEmailValidationData(
                user_id=user_id,
                file_id=bulk_stat.id,
                file_name=file_name,
                emails=[single_email_validation_response(e) for e in test_email_objs],
            )
        except IntegrityError:
            self.db.rollback()
            return error_response(message="Failed to save eamil records", data=None)

    def update_file_name_by_id(self, file_id: int, new_filename: str, user_id: int) -> Union[str, JSONResponse]:
        db_filename = (
            self.db.query(FileValidation)
            .filter(
                FileValidation.id == file_id,
                FileValidation.user_id == user_id,
                or_(FileValidation.soft_delete.is_(None), FileValidation.soft_delete.is_(False)),
            )
            .first()
        )

        if not db_filename:
            return error_response(message="File not found.", status_code=status.HTTP_404_NOT_FOUND, data=None)

        db_filename.file_name = new_filename
        self.db.commit()
        self.db.refresh(db_filename)

        return db_filename.file_name

    def soft_delete_file_by_file_id(self, file_id: int, user_id: int):
        bulk_emails = (
            self.db.query(FileValidation)
            .filter(
                FileValidation.id == file_id,
                FileValidation.user_id == user_id,
                or_(
                    FileValidation.soft_delete.is_(False),
                    FileValidation.soft_delete.is_(None),
                ),
            )
            .first()
        )

        if not bulk_emails:
            return error_response(message="File emails not found.", status_code=status.HTTP_404_NOT_FOUND, data=None)

        associated_emails = (
            self.db.query(SingleValidation)
            .filter(
                SingleValidation.file_id == file_id,
                SingleValidation.user_id == user_id,
                or_(
                    SingleValidation.soft_delete.is_(False),
                    SingleValidation.soft_delete.is_(None),
                ),
            )
            .all()
        )

        for associated_email in associated_emails:
            associated_email.soft_delete = True

        self.db.flush(associated_emails)

        bulk_emails.soft_delete = True
        self.db.commit()
        self.db.refresh(bulk_emails)
        result = FileDeletion(
            file_name=bulk_emails.file_name, emails=[email.validated_email for email in associated_emails]
        )
        return result

    def get_emails_for_csv(self, file_id: int, user_id: int, include_risky: bool):
        query = self.db.query(SingleValidation).filter(
            SingleValidation.file_id == file_id,
            SingleValidation.user_id == user_id,
            SingleValidation.soft_delete.is_(False),
        )

        if include_risky is False:
            query = query.filter(SingleValidation.is_risky.is_(False))
        # if False, do not filter by is_risky (i.e., return all)

        return query.all()

    def get_all_files_with_delieved_emails_and_status(self, user_id: int):
        files = (
            self.db.query(FileValidation)
            .filter(FileValidation.user_id == user_id, FileValidation.soft_delete == False)  # noqa: E712
            .order_by(FileValidation.created_at.desc())  # 👈 sort by latest
            .all()
        )
        result = []

        for file in files:
            total_emails = (
                self.db.query(SingleValidation)
                .filter(SingleValidation.file_id == file.id, SingleValidation.user_id == user_id)
                .count()
            )

            deliverable_count = (
                self.db.query(SingleValidation)
                .filter(
                    SingleValidation.file_id == file.id,
                    SingleValidation.user_id == user_id,
                    SingleValidation.is_deliverable.is_(True),
                )
                .count()
            )

            result.append(
                {
                    "id": file.id,
                    "file_name": file.file_name,
                    "deliverable": deliverable_count,
                    "total_emails": total_emails,
                    "status": file.status,
                }
            )

        return result
