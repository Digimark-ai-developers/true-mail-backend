import io
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Load secrets into os.environ before any app imports
try:
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    from dotenv import load_dotenv
    load_dotenv()

from app.database.db_config import SessionLocal
from app.models.email import BulkEmailStats, TestEmail
from app.utils.mail_utils import (
    load_disposable_domains,
    validate_email_syntax,
    get_mx_record,
    perform_email_checks,
    get_smtp_provider,
    evaluate_email_score_and_risk,
)

st.set_page_config(page_title="True Mail Validator", layout="wide")
st.title("True Mail Validator")

SENDER_EMAIL = "test@example.com"
TEST_USER_ID = os.getenv("STREAMLIT_USER_ID", "streamlit-user")

disposable_domains = load_disposable_domains()


def process_email(email):
    domain = email.split("@", 1)[-1].lower() if "@" in email else ""
    is_syntax_valid = validate_email_syntax(email)
    mx_result = get_mx_record(domain)
    mx_record = mx_result[0] if mx_result else None
    implicit_mx = mx_result[1] if mx_result and len(mx_result) > 1 else None
    smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
        target_email=email, sender_email=SENDER_EMAIL, disposable_domains=disposable_domains
    )
    is_disposable = domain in disposable_domains
    has_role = any(r in email for r in ["admin", "info", "support", "sales", "contact"])
    is_accept_all = "accept" in email or "all" in email
    has_no_reply = "no-reply" in email or "noreply" in email
    smtp_provider = get_smtp_provider(domain)
    score, is_risky, tags = evaluate_email_score_and_risk(
        is_syntax_valid=is_syntax_valid,
        smtp_deliverable=smtp_deliverable,
        is_disposable=is_disposable,
        has_role=has_role,
        is_accept_all=is_accept_all,
        has_no_reply=has_no_reply,
        domain=domain,
        mx_record=mx_record,
        smtp_provider=smtp_provider,
    )
    is_email_valid = is_syntax_valid and smtp_deliverable
    return {
        "email": email,
        "domain": domain,
        "status": "valid" if is_email_valid else "invalid",
        "reason": validation_reason or smtp_reason,
        "is_deliverable": smtp_deliverable,
        "is_risky": is_risky,
        "is_valid": is_email_valid,
        "is_disposable": is_disposable,
        "is_syntax_valid": is_syntax_valid,
        "smtp_provider": smtp_provider,
        "mx_record": mx_record or "",
        "implicit_mx_record": implicit_mx,
        "score": score,
        "has_role": has_role,
        "is_accept_all": is_accept_all,
        "has_no_reply": has_no_reply,
        "alphabetical_characters": sum(c.isalpha() for c in email),
        "has_numerical_characters": sum(c.isdigit() for c in email),
        "has_unicode_symbols": len(email) - sum(c.isalpha() for c in email) - sum(c.isdigit() for c in email),
    }


def save_to_db(file_name, emails, results):
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        duplicate_count = len(emails) - len(set(emails))
        deliverable = sum(1 for r in results if r["is_deliverable"])
        risky = sum(1 for r in results if r["is_risky"])
        total = len(emails)
        deliverable_pct = int((deliverable / total) * 100) if total else 0

        bulk = BulkEmailStats(
            user_id=TEST_USER_ID,
            file_name=file_name,
            duplicate_email=duplicate_count,
            total_valid_emails=deliverable,
            deliverable=deliverable_pct,
            risky=risky,
            status="Completed",
            total=total,
            created_at=now,
            soft_delete=False,
        )
        db.add(bulk)
        db.flush()

        for r in results:
            local_part = r["email"].split("@")[0]
            full_name = " ".join(
                p.capitalize()
                for p in local_part.replace(".", " ").replace("_", " ").replace("-", " ").split()
            )
            te = TestEmail(
                user_id=TEST_USER_ID,
                file_id=bulk.id,
                user_tested_email=r["email"],
                full_name=full_name or "N/A",
                gender="Unknown",
                status=r["status"],
                reason=r["reason"],
                domain=r["domain"],
                is_free=False,
                is_risky=r["is_risky"],
                is_valid=r["is_valid"],
                is_disposable=r["is_disposable"],
                is_deliverable=r["is_deliverable"],
                has_tag=False,
                alphabetical_characters=r["alphabetical_characters"],
                is_mailbox_full=False,
                has_role=r["has_role"],
                is_accept_all=r["is_accept_all"],
                has_numerical_characters=r["has_numerical_characters"],
                has_unicode_symbols=r["has_unicode_symbols"],
                has_no_reply=r["has_no_reply"],
                smtp_provider=r["smtp_provider"],
                mx_record=r["mx_record"],
                implicit_mx_record=r["implicit_mx_record"],
                score=r["score"],
                soft_delete=False,
                created_at=now,
            )
            db.add(te)

        db.commit()
        return bulk.id
    except Exception as e:
        db.rollback()
        st.warning(f"DB save failed: {e}")
        return None
    finally:
        db.close()


uploaded_file = st.file_uploader("Upload CSV (must have an 'Email' column)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    col = next((c for c in df.columns if c.strip().lower() == "email"), None)
    if not col:
        st.error("No 'Email' column found in CSV.")
    else:
        emails = df[col].dropna().str.strip().str.lower().tolist()
        unique_emails = list(dict.fromkeys(emails))
        st.info(f"Found {len(unique_emails)} unique emails ({len(emails) - len(unique_emails)} duplicates removed).")

        if st.button("Start Validation"):
            progress = st.progress(0)
            status_text = st.empty()
            results = []

            for i, email in enumerate(unique_emails):
                status_text.text(f"Checking {i+1}/{len(unique_emails)}: {email}")
                results.append(process_email(email))
                progress.progress((i + 1) / len(unique_emails))

            status_text.text("Saving to database...")
            file_id = save_to_db(uploaded_file.name, emails, results)
            status_text.text("Done!")

            total = len(results)
            deliverable = sum(1 for r in results if r["is_deliverable"])
            risky = sum(1 for r in results if r["is_risky"])
            invalid = total - deliverable

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", total)
            c2.metric("Deliverable", deliverable)
            c3.metric("Risky", risky)
            c4.metric("Invalid", invalid)

            if file_id:
                st.success(f"Saved to DB — File ID: {file_id}")

            result_df = pd.DataFrame([{
                "Email": r["email"],
                "Status": r["status"].capitalize(),
                "Deliverable": r["is_deliverable"],
                "Risky": r["is_risky"],
                "Score": r["score"],
                "Provider": r["smtp_provider"],
                "Reason": r["reason"],
            } for r in results])

            st.dataframe(result_df, use_container_width=True)

            csv_out = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Results CSV", csv_out, "results.csv", "text/csv")
