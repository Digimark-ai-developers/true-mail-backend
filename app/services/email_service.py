import asyncio
import csv
import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.credits import Credit, CreditUsage
from app.models.email import BulkEmailStats, TestEmail
from app.models.user import User
from app.schemas.email import (
    BulkEmailStatsCreateWithEmails,
    BulkEmailStatsResponseWithEmails,
    CreditUsageBase,
    TestEmailBase,
)
from app.services.credit_service import CreditService
from app.utils.mail_utils import (
    analyze_email,
    evaluate_email_score_and_risk,
    get_mx_record,
    get_smtp_provider,
    load_disposable_domains,
    perform_email_checks,
    validate_email_syntax,
)

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, db: Session):
        self.db = db

    async def create_test_email(self, user_id: str, test_email: TestEmailBase, sender_email: str = "test@example.com"):
        # Step 1: Validate User
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="User ID not found")

        # Step 2: Check and Deduct Credits
        credit = self.db.query(Credit).filter(Credit.user_id == user_id).first()
        if not credit or credit.remaining_credits < 1:
            raise HTTPException(status_code=403, detail="Insufficient credits to test email")

        credit.remaining_credits -= 1
        credit.total_credits -= 1
        credit.last_updated = datetime.utcnow()
        self.db.add(credit)

        # Step 3: Email Validations
        target_email = test_email.user_tested_email
        if not target_email:
            raise HTTPException(status_code=400, detail="No email provided to validate.")

        disposable_domains = load_disposable_domains()
        is_syntax_valid = validate_email_syntax(target_email)

        # Step 4: Safely Handle MX Record
        mx_record_result = get_mx_record(target_email)
        mx_record = mx_record_result[0] if mx_record_result else None
        implicit_mx = mx_record_result[1] if mx_record_result and len(mx_record_result) > 1 else None

        # Step 5: Run consolidated email checks
        smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
            target_email=target_email, sender_email=sender_email, disposable_domains=disposable_domains
        )

        email_domain = target_email.split("@")[-1].lower()
        is_disposable = int(email_domain in disposable_domains)

        email_domain = target_email.split("@")[-1].lower()
        # is_deliverable = int(email_domain in disposable_domains)

        # Extract domain part (e.g., "gmail" from "test@gmail.com")
        domain_name = target_email.split("@")[-1].split(".")[0]
        match = re.search(r"@([\w\-]+)\.", target_email)
        domain_name = match.group(1) if match else None
        # Extract domain and name from email

        local_part = re.sub(r"[^a-zA-Z._-]", "", target_email.split("@")[0])  # Remove numbers/symbols except separators
        cleaned_name = re.sub(r"[\._-]+", " ", local_part).strip()  # Replace _, ., - with space
        full_name = " ".join(part.capitalize() for part in cleaned_name.split())

        # Step 5.1: Analyze email string
        email_str = target_email or ""
        alphabetical_count = sum(c.isalpha() for c in email_str)
        numerical_count = sum(c.isdigit() for c in email_str)
        unicode_symbol_count = len(email_str) - alphabetical_count - numerical_count
        email_str = target_email.lower()
        has_role = any(role in email_str for role in ["admin", "info", "support", "sales", "contact"])
        is_accept_all = "accept" in email_str or "all" in email_str
        has_no_reply = "no-reply" in email_str or "noreply" in email_str

        # Extract domain for smtp_provider detection
        try:
            _, domain = target_email.split("@")
        except ValueError:
            domain = ""

        smtp_provider = get_smtp_provider(domain)

        # Refined score & risk evaluation
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

        # Step 6: Prepare data dictionary with overrides
        email_data = test_email.model_dump()
        email_data.update(
            {
                # "status": "valid" if is_valid else "invalid",
                # "is_deliverable": is_deliverable,
                # "implicit_mx_record": implicit_mx,
                # "mx_record": mx_record,
                "user_id": user_id,
                "full_name": full_name or "N/A",
                "domain": domain_name,
                "created_at": datetime.now(timezone.utc),
                "is_risky": is_risky,
                "soft_delete": False,
                "is_valid": is_syntax_valid and smtp_deliverable,
                "status": "valid" if is_syntax_valid and smtp_deliverable else "invalid",
                "is_deliverable": smtp_deliverable,
                "reason": validation_reason or smtp_reason,
                "is_disposable": is_disposable,
                "alphabetical_characters": alphabetical_count,
                "has_numerical_characters": numerical_count,
                "has_unicode_symbols": unicode_symbol_count,
                "smtp_provider": smtp_provider,
                "mx_record": mx_record or "",
                "implicit_mx_record": implicit_mx,
                "score": score,
                "has_role": has_role,
                "is_accept_all": is_accept_all,
                "has_no_reply": has_no_reply,
            }
        )

        # Step 7: Create DB record
        db_test_email = TestEmail(**email_data)
        self.db.add(db_test_email)
        self.db.commit()
        self.db.refresh(db_test_email)

        # Step 8: Record credit usage
        credit_used = CreditUsageBase(
            user_id=user_id,
            email_or_file_id=db_test_email.id,
            quantity_used=1,
            credits_used=1,
            created_at=datetime.now(timezone.utc),
        )
        db_credit_used = CreditUsage(**credit_used.model_dump())
        self.db.add(db_credit_used)

        try:
            self.db.commit()
            self.db.refresh(db_test_email)
            return db_test_email
        except IntegrityError:
            self.db.rollback()
            logger.exception("Database error during create_test_email.")
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while testing email",
            )

    async def process_bulk_email_file(self, file, user_id: str, db: Session):
        file_contents = file.file.read().decode("utf-8")
        csv_reader = csv.reader(io.StringIO(file_contents))
        emails = [row[0].strip() for row in csv_reader if row]

        file_name = file.filename or "test_email.csv"
        file_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        seen_emails = set()
        duplicate_count = 0
        valid_count = 0
        total_count = 0

        bulk_email_objects = []
        test_email_objects = []

        # Helper function for processing each email
        async def process_email(email):
            nonlocal duplicate_count, valid_count, total_count

            total_count += 1
            if email in seen_emails:
                duplicate_count += 1
                return None
            seen_emails.add(email)

            result = await analyze_email(email)

            # Prepare email data for database insertion
            email_data = {
                "user_id": user_id,
                "full_name": result.get("full_name", "N/A"),
                "domain": result.get("domain_name"),
                "created_at": created_at,
                "is_risky": result.get("is_risky"),
                "soft_delete": False,
                "is_valid": result.get("is_syntax_valid") and result.get("smtp_deliverable"),
                "status": "valid" if result.get("is_syntax_valid") and result.get("smtp_deliverable") else "invalid",
                "is_deliverable": result.get("smtp_deliverable"),
                "reason": result.get("validation_reason") or result.get("smtp_reason"),
                "is_disposable": result.get("is_disposable"),
                "alphabetical_characters": result.get("alphabetical_count"),
                "has_numerical_characters": result.get("numerical_count"),
                "has_unicode_symbols": result.get("unicode_symbol_count"),
                "smtp_provider": result.get("smtp_provider"),
                "mx_record": result.get("mx_record", ""),
                "implicit_mx_record": result.get("implicit_mx"),
                "score": result.get("score"),
                "has_role": result.get("has_role"),
                "is_accept_all": result.get("is_accept_all"),
                "has_no_reply": result.get("has_no_reply"),
                "file_id": file_id,
                "file_name": file_name,
                "email_status": "processing",
            }

            # Append email data to the bulk list
            bulk_email_objects.append(TestEmail(**email_data))

            # Add to test emails if the file name is 'test_email.csv'
            if file_name == "test_email.csv":
                test_email_objects.append(BulkEmailStats(**email_data))

            if email_data["is_valid"]:
                valid_count += 1

        # Concurrently process emails using asyncio.gather()
        tasks = [process_email(email) for email in emails]
        await asyncio.gather(*tasks)

        # Store all email data in the DB
        db.bulk_save_objects(bulk_email_objects)
        if test_email_objects:
            db.bulk_save_objects(test_email_objects)

        # Store bulk upload summary (metadata) in BulkEmailStats table
        bulk_email_summary = {
            "user_id": user_id,
            "file_id": file_id,
            "file_name": file_name,
            "total": total_count,
            "duplicate_email": duplicate_count,
            "total_valid_emails": valid_count,
            "email_status": "completed",
            "created_at": created_at,
        }
        db.add(BulkEmailStats(**bulk_email_summary))

        # Update credits for valid emails only
        if valid_count:
            credit_service = CreditService()
            credit_service.decrement_credits(db, user_id=user_id, amount=valid_count)

        db.commit()

        return {
            "file_id": file_id,
            "file_name": file_name,
            "total": total_count,
            "duplicate_email": duplicate_count,
            "total_valid_emails": valid_count,
            "email_status": "completed",
            "created_at": created_at,
        }

    def get_test_email(self, test_email_id: int):
        test_email = (
            self.db.query(TestEmail)
            .filter(
                TestEmail.id == test_email_id, or_(TestEmail.soft_delete.is_(False), TestEmail.soft_delete.is_(None))
            )
            .first()
        )
        if not test_email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test email not found")

        return test_email

    def get_all_test_emails(self, user_id: str) -> List[TestEmail]:
        return (
            self.db.query(TestEmail)
            .filter(TestEmail.user_id == user_id)
            .filter(or_(TestEmail.soft_delete.is_(None), TestEmail.soft_delete.is_(False)))
            .all()
        )

    def process_bulk_email_filee(self, file: UploadFile, user_id: str) -> BulkEmailStatsResponseWithEmails:
        # ✅ Step 1: Read and extract emails from file
        try:
            contents = file.file.read().decode("utf-8")
            extension = os.path.splitext(file.filename)[1].lower()

            if extension not in [".csv", ".txt"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported file type. Only CSV and TXT are allowed.",
                )

            # Always treat content as comma-separated regardless of file type
            emails = [email.strip().lower() for email in contents.split(",") if email.strip()]

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not read the uploaded file. Make sure it's properly formatted.",
            )
        finally:
            file.file.close()

        if not emails:
            raise HTTPException(status_code=400, detail="No valid emails found")

        credit = self.db.query(Credit).filter(Credit.user_id == user_id).first()
        if not credit or credit.remaining_credits < len(emails):
            raise HTTPException(status_code=403, detail="Insufficient credits")

        total_emails = len(emails)
        unique_emails = set(emails)
        duplicate_count = total_emails - len(unique_emails)

        total_valid = 0
        risky_count = 0
        deliverable_count = 0

        for email in emails:
            if email.endswith("@gmail.com"):
                total_valid += 1
                deliverable_count += 1
            elif "test" in email:
                risky_count += 1

        deliverable_percent = (deliverable_count / total_emails) * 100 if total_emails > 0 else 0

        bulk_stat = BulkEmailStats(
            user_id=user_id,
            file_name=file.filename,
            duplicate_email=duplicate_count,
            total_valid_emails=total_valid,
            deliverable=deliverable_percent,
            total=total_emails,
            created_at=datetime.now(timezone.utc),
            soft_delete=False,
        )
        self.db.add(bulk_stat)
        self.db.commit()
        self.db.refresh(bulk_stat)

        test_email_objs = []
        for email in emails:
            test_email_obj = TestEmail(
                user_id=user_id,
                file_id=bulk_stat.id,
                user_tested_email=email,
                full_name="Unknown",
                gender="Unknown",
                status="Pending",
                reason="N/A",
                domain="unknown.com",
                is_free=False,
                is_risky=False,
                is_valid=False,
                is_disposable=False,
                is_deliverable=False,
                has_tag=False,
                alphabetical_characters=0,
                is_mailbox_full=False,
                has_role=False,
                is_accept_all=False,
                has_numerical_characters=0,
                has_unicode_symbols=0,
                has_no_reply=False,
                smtp_provider="Unknown",
                mx_record="N/A",
                implicit_mx_record="N/A",
                score=0,
                soft_delete=False,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(test_email_obj)
            test_email_objs.append(test_email_obj)

        credit.remaining_credits -= total_emails
        credit.total_credits -= total_emails
        credit.last_updated = datetime.utcnow()
        self.db.add(credit)

        credit_used = CreditUsageBase(
            user_id=user_id,
            email_or_file_id=bulk_stat.id,
            quantity_used=total_emails,
            credits_used=total_emails,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(CreditUsage(**credit_used.model_dump()))

        try:
            self.db.commit()
            return BulkEmailStatsResponseWithEmails(
                user_id=user_id,
                file_id=bulk_stat.id,
                file_name=bulk_stat.file_name,
                test_emails=[e.user_tested_email for e in test_email_objs],
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Failed to save email records")

    def get_all_emails_grouped_by_files(self, user_id: str):
        # Get all bulk files belonging to the user (excluding soft deleted ones)
        bulk_files = (
            self.db.query(BulkEmailStats)
            .filter(
                BulkEmailStats.user_id == user_id,
                or_(BulkEmailStats.soft_delete.is_(False), BulkEmailStats.soft_delete.is_(None)),
            )
            .all()
        )

        results = []

        for bulk_file in bulk_files:
            test_emails = [email for email in bulk_file.test_emails if not email.soft_delete]

            results.append({"file_id": bulk_file.id, "file_name": bulk_file.file_name, "emails": test_emails})

        return results

    def get_file_stats(self, file_id: int, user_id: str):
        total_emails = (
            self.db.query(TestEmail).filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id).count()
        )

        if total_emails == 0:
            return None
        duplicate_count = (
            self.db.query(BulkEmailStats.duplicate_email)
            .filter(BulkEmailStats.id == file_id, BulkEmailStats.user_id == user_id)
            .scalar()
        )

        deliverable_count = (
            self.db.query(TestEmail)
            .filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id, TestEmail.is_deliverable.is_(True))
            .count()
        )

        risky_count = (
            self.db.query(TestEmail)
            .filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id, TestEmail.is_risky.is_(True))
            .count()
        )

        undeliverable_count = total_emails - deliverable_count

        return {
            "total": total_emails,
            "duplicates": duplicate_count,
            "deliverable": deliverable_count,
            "undeliverable": undeliverable_count,
            "risky": risky_count,
            "duplicated_percentage": round((duplicate_count / total_emails) * 100, 2),
            "deliverable_percentage": round((deliverable_count / total_emails) * 100, 2),
            "undeliverable_percentage": round((undeliverable_count / total_emails) * 100, 2),
            "risky_percentage": round((risky_count / total_emails) * 100, 2),
        }

    def create_bulk_email_with_copy_paste(self, payload: BulkEmailStatsCreateWithEmails, user_id: str):
        email_count = len(payload.test_emails)

        # Step 1: Check credit
        credit = self.db.query(Credit).filter(Credit.user_id == user_id).first()
        if not credit or credit.remaining_credits < email_count:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient credits to test all emails",
            )

        # Step 2: Prepare stats
        emails = [email.lower() for email in payload.test_emails]
        total_emails = len(emails)
        unique_emails = set(emails)
        duplicate_count = total_emails - len(unique_emails)

        total_valid = 0
        risky_count = 0
        deliverable_count = 0

        for email in emails:
            if email.endswith("@gmail.com"):
                total_valid += 1
                deliverable_count += 1
            elif "test" in email:
                risky_count += 1

        deliverable_percent = (deliverable_count / total_emails) * 100 if total_emails > 0 else 0

        bulk_stat = BulkEmailStats(
            user_id=user_id,
            file_name="Copy/Paste",
            duplicate_email=duplicate_count,
            total_valid_emails=total_valid,
            deliverable=deliverable_percent,
            total=total_emails,
            soft_delete=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(bulk_stat)
        self.db.commit()
        self.db.refresh(bulk_stat)

        # Step 3: Add test emails
        test_email_objs = []
        for test_email in payload.test_emails:
            test_email_obj = TestEmail(
                user_id=bulk_stat.user_id,
                file_id=bulk_stat.id,
                user_tested_email=test_email,
                full_name="Unknown",
                gender="Unknown",
                status="Pending",
                reason="N/A",
                domain="unknown.com",
                is_free=False,
                is_valid=False,
                is_disposable=False,
                is_deliverable=False,
                is_risky=False,
                has_tag=False,
                alphabetical_characters=0,
                is_mailbox_full=False,
                has_role=False,
                is_accept_all=False,
                has_numerical_characters=0,
                has_unicode_symbols=0,
                has_no_reply=False,
                smtp_provider="Unknown",
                mx_record="N/A",
                implicit_mx_record="N/A",
                score=0,
                soft_delete=False,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(test_email_obj)
            test_email_objs.append(test_email_obj)

        # Step 4: Deduct credits
        credit.remaining_credits -= email_count
        credit.total_credits -= email_count
        credit.last_updated = datetime.utcnow()
        self.db.add(credit)

        credit_used = CreditUsageBase(
            user_id=user_id,
            email_or_file_id=bulk_stat.id,
            quantity_used=email_count,
            credits_used=email_count,
            created_at=datetime.now(timezone.utc),
        )
        db_credit_used = CreditUsage(**credit_used.model_dump())
        self.db.add(db_credit_used)

        try:
            self.db.commit()
            return BulkEmailStatsResponseWithEmails(
                user_id=user_id,
                file_id=bulk_stat.id,
                file_name=bulk_stat.file_name,
                test_emails=[email.user_tested_email for email in test_email_objs],
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not save email records",
            )

    def update_file_name_by_id(self, file_id: int, new_filename: str, user_id: str) -> str:
        db_filename = (
            self.db.query(BulkEmailStats)
            .filter(
                BulkEmailStats.id == file_id,
                BulkEmailStats.user_id == user_id,
                or_(BulkEmailStats.soft_delete.is_(None), BulkEmailStats.soft_delete.is_(False)),
            )
            .first()
        )

        if not db_filename:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

        db_filename.file_name = new_filename
        self.db.commit()
        self.db.refresh(db_filename)

        return db_filename.file_name

    def soft_delete_test_email_by_id(self, test_email_id: int, user_id: str) -> dict:
        db_test_email = (
            self.db.query(TestEmail)
            .filter(
                TestEmail.id == test_email_id,
                TestEmail.user_id == user_id,
                TestEmail.file_id.is_(None),
                or_(TestEmail.soft_delete.is_(False), TestEmail.soft_delete.is_(None)),
            )
            .first()
        )

        if not db_test_email:
            raise HTTPException(status_code=404, detail="Test email not found.")

        db_test_email.soft_delete = True
        self.db.commit()
        self.db.refresh(db_test_email)

        return jsonable_encoder(db_test_email)

    def soft_delete_bulk_emails_file_by_id(self, file_id: int, user_id: str):
        bulk_emails = (
            self.db.query(BulkEmailStats)
            .filter(
                BulkEmailStats.id == file_id,
                BulkEmailStats.user_id == user_id,
                or_(
                    BulkEmailStats.soft_delete.is_(False),
                    BulkEmailStats.soft_delete.is_(None),
                ),
            )
            .first()
        )

        if not bulk_emails:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bulk emails file not found.",
            )

        bulk_emails.soft_delete = True
        self.db.commit()
        self.db.refresh(bulk_emails)
        return bulk_emails

    def get_emails_for_csv(self, file_id: int, user_id: str, include_risky: bool):
        query = self.db.query(TestEmail).filter(
            TestEmail.file_id == file_id, TestEmail.user_id == user_id, TestEmail.soft_delete.is_(False)
        )

        if include_risky is False:
            query = query.filter(TestEmail.is_risky.is_(False))
        elif include_risky is True:
            query = query.filter(TestEmail.is_risky.is_(True))

        return query.all()
