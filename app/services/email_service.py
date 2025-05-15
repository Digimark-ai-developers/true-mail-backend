from datetime import datetime, timezone
import os
from typing import List
from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.credits import Credit, CreditUsage
from app.models.email import BulkEmailStats, TestEmail
from app.models.user import User
from app.schemas.email import BulkEmailStatsCreateWithEmails, BulkEmailStatsResponseWithEmails, CreditUsageBase, TestEmailBase


class EmailService:
    def __init__(self, db: Session):
        self.db = db

    def create_test_email(self, user_id: str, test_email: TestEmailBase):
        # Validate user
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID not found")

        # Validate and deduct credit
        credit = self.db.query(Credit).filter(Credit.user_id == user_id).first()
        if not credit or credit.remaining_credits < 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient credits to test email")

        credit.remaining_credits -= 1
        credit.total_credits -= 1
        credit.last_updated = datetime.utcnow()
        self.db.add(credit)

        # Create TestEmail entry
        db_test_email = TestEmail(**test_email.model_dump(), user_id=user_id, created_at=datetime.now(timezone.utc), soft_delete=False)
        self.db.add(db_test_email)
        self.db.commit()
        self.db.refresh(db_test_email)

        # Create credit usage record
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )

    def get_test_email(self, test_email_id: int):
        test_email = (
            self.db.query(TestEmail)
            .filter(TestEmail.id == test_email_id, or_(TestEmail.soft_delete.is_(False), TestEmail.soft_delete.is_(None)))
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

    def process_bulk_email_file(self, file: UploadFile, user_id: str) -> BulkEmailStatsResponseWithEmails:
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
            is_risky=risky_count > 0,
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
            .filter(BulkEmailStats.user_id == user_id, or_(BulkEmailStats.soft_delete.is_(False), BulkEmailStats.soft_delete.is_(None)))
            .all()
        )

        results = []

        for bulk_file in bulk_files:
            test_emails = [email for email in bulk_file.test_emails if not email.soft_delete]

            results.append({"file_id": bulk_file.id, "file_name": bulk_file.file_name, "emails": test_emails})

        return results

    def get_file_stats(self, file_id: int, user_id: str):
        total_emails = self.db.query(TestEmail).filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id).count()

        if total_emails == 0:
            return None

        duplicate_count = (
            self.db.query(TestEmail.user_tested_email)
            .filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id)
            .group_by(TestEmail.user_tested_email)
            .having(func.count(TestEmail.user_tested_email) > 1)
            .count()
        )

        deliverable_count = (
            self.db.query(TestEmail).filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id, TestEmail.is_deliverable.is_(True)).count()
        )

        risky_count = self.db.query(TestEmail).filter(TestEmail.file_id == file_id, TestEmail.user_id == user_id, TestEmail.reason == "Risky").count()

        undeliverable_count = total_emails - deliverable_count

        return {
            "total": total_emails,
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
            is_risky=False,
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
