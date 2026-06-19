import os
import time
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
from app.models.user import User
from app.models.credits import Credit
from app.models.email import BulkEmailStats, TestEmail
from app.utils.mail_utils import (
    load_disposable_domains,
    validate_email_syntax,
    get_mx_record,
    perform_email_checks,
    get_smtp_provider,
    evaluate_email_score_and_risk,
)

st.set_page_config(page_title="Email Validity and Reachability Checker", layout="wide")

disposable_domains = load_disposable_domains()

# Sidebar
with st.sidebar:
    st.info(f"Loaded {len(disposable_domains)} disposable email domains")
    with st.expander("Configuration", expanded=True):
        st.caption("App configuration and settings")

# Main title
st.title("Email Validity and Reachability Checker")
st.caption("Validate email addresses with enhanced SMTP server validation.")

# Advanced settings
with st.expander("Advanced Settings", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        sender_email = st.text_input("Sender Email Address", value="test@example.com")
        delay_between_emails = st.slider("Delay Between Emails (seconds)", 0.10, 3.00, 0.50, step=0.10)
    with col2:
        verification_timeout = st.slider("Verification Timeout (seconds)", 3, 15, 7)
        delay_between_domains = st.slider("Delay Between Domains (seconds)", 1.00, 10.00, 2.00, step=0.50)

    skip_smtp = st.checkbox("Skip detailed SMTP verification (faster but less accurate)")
    treat_catchall_valid = st.checkbox("Treat catch-all domains as valid", value=True)

# Mode selection
mode = st.radio("Select Mode", ["Single Email", "Batch (CSV File)"])

SENDER_EMAIL = sender_email


def process_email(email, timeout=7, skip_smtp_check=False, catchall_valid=True):
    domain = email.split("@", 1)[-1].lower() if "@" in email else ""
    is_syntax_valid = validate_email_syntax(email)
    if not is_syntax_valid:
        return _result(email, domain, False, False, "Invalid email syntax", None, None, None, False, False, False)

    mx_result = get_mx_record(domain)
    mx_record = mx_result[0] if mx_result else None
    implicit_mx = mx_result[1] if mx_result and len(mx_result) > 1 else None

    if not mx_record:
        return _result(email, domain, False, False, "MX lookup failed", mx_record, implicit_mx, None, False, False, False)

    is_disposable = domain in disposable_domains
    if is_disposable:
        return _result(email, domain, False, False, "Disposable email address", mx_record, implicit_mx, None, False, True, False)

    smtp_provider = get_smtp_provider(domain)

    if skip_smtp_check:
        smtp_deliverable = True
        validation_reason = "SMTP check skipped"
        smtp_reason = "SMTP check skipped"
        is_valid = True
    else:
        smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
            target_email=email, sender_email=SENDER_EMAIL, disposable_domains=disposable_domains, timeout=timeout
        )

    has_role = any(r in email for r in ["admin", "info", "support", "sales", "contact"])
    is_accept_all = "accept" in email or "all" in email
    has_no_reply = "no-reply" in email or "noreply" in email

    if catchall_valid and is_accept_all:
        smtp_deliverable = True
        validation_reason = "Catch-all domain treated as valid"

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
        "status": "Valid" if is_email_valid else "Invalid",
        "reason": validation_reason or smtp_reason,
        "is_deliverable": smtp_deliverable,
        "is_risky": is_risky,
        "is_valid": is_email_valid,
        "is_disposable": is_disposable,
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


def _result(email, domain, deliverable, valid, reason, mx, implicit_mx, provider, risky, disposable, accept_all):
    return {
        "email": email, "domain": domain,
        "status": "Valid" if valid else "Invalid",
        "reason": reason,
        "is_deliverable": deliverable,
        "is_risky": risky,
        "is_valid": valid,
        "is_disposable": disposable,
        "smtp_provider": provider or "Unknown",
        "mx_record": mx or "",
        "implicit_mx_record": implicit_mx,
        "score": 0,
        "has_role": False,
        "is_accept_all": accept_all,
        "has_no_reply": False,
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
            user_id="streamlit-user",
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
                user_id="streamlit-user",
                file_id=bulk.id,
                user_tested_email=r["email"],
                full_name=full_name or "N/A",
                gender="Unknown",
                status=r["status"].lower(),
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


# ── Single Email Mode ──────────────────────────────────────────────────────────
if mode == "Single Email":
    email_input = st.text_input("Enter Email Address to Validate")
    if st.button("Validate Email"):
        if not email_input.strip():
            st.warning("Please enter an email address.")
        else:
            with st.spinner("Validating..."):
                result = process_email(
                    email_input.strip().lower(),
                    timeout=verification_timeout,
                    skip_smtp_check=skip_smtp,
                    catchall_valid=treat_catchall_valid,
                )
            if result["is_deliverable"]:
                st.success(f"✅ Valid — {result['reason']}")
            elif result["is_risky"]:
                st.warning(f"⚠️ Risky — {result['reason']}")
            else:
                st.error(f"❌ Invalid — {result['reason']}")

            with st.expander("Full Details"):
                st.json({k: v for k, v in result.items() if k != "email"})

# ── Batch Mode ─────────────────────────────────────────────────────────────────
else:
    uploaded_file = st.file_uploader("Upload CSV (must have an 'Email' column)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        col = next((c for c in df.columns if c.strip().lower() == "email"), None)
        if not col:
            st.error("No 'Email' column found in CSV.")
        else:
            emails = df[col].dropna().str.strip().str.lower().tolist()
            unique_emails = list(dict.fromkeys(emails))
            duplicates = len(emails) - len(unique_emails)
            st.info(f"Found {len(unique_emails)} unique emails ({duplicates} duplicates removed).")

            if st.button("Start Validation"):
                progress = st.progress(0)
                status_text = st.empty()
                results = []
                last_domain = None

                for i, email in enumerate(unique_emails):
                    status_text.text(f"Checking {i+1}/{len(unique_emails)}: {email}")
                    domain = email.split("@", 1)[-1] if "@" in email else ""

                    if last_domain and domain != last_domain:
                        time.sleep(delay_between_domains)
                    else:
                        time.sleep(delay_between_emails)

                    results.append(process_email(
                        email,
                        timeout=verification_timeout,
                        skip_smtp_check=skip_smtp,
                        catchall_valid=treat_catchall_valid,
                    ))
                    last_domain = domain
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
                    "Status": r["status"],
                    "Deliverable": r["is_deliverable"],
                    "Risky": r["is_risky"],
                    "Score": r["score"],
                    "Provider": r["smtp_provider"],
                    "Reason": r["reason"],
                } for r in results])

                st.dataframe(result_df, use_container_width=True)

                csv_out = result_df.to_csv(index=False).encode("utf-8")
                st.download_button("Download Results CSV", csv_out, "results.csv", "text/csv")
