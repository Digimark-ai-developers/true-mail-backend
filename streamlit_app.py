import os
import time
import uuid
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

# ── Session state init ─────────────────────────────────────────────────────────
for _k, _v in [
    ("batch_results", None),
    ("batch_file_id", None),
    ("batch_db_error", None),
    ("batch_done", False),
    ("batch_original_df", None),
    ("batch_email_col", None),
    ("batch_task_id", None),
    ("batch_logs", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Screen Wake Lock ──────────────────────────────────────────────────────────
def keep_screen_awake(active: bool) -> None:
    """Hold a Screen Wake Lock while a job runs; release when idle.
    Graceful no-op where the API is unsupported."""
    flag = "true" if active else "false"
    st.components.v1.html(
        """<script>
        (function(){
          try{
            var w = window.parent;
            w.__evWantWake = %s;
            if(!w.__evWakeInit){
              w.__evWakeInit = true; w.__evWakeLock = null;
              w.__evAcquire = async function(){
                try{
                  if(w.__evWantWake && 'wakeLock' in w.navigator && !w.__evWakeLock){
                    w.__evWakeLock = await w.navigator.wakeLock.request('screen');
                    w.__evWakeLock.addEventListener('release', function(){ w.__evWakeLock = null; });
                  }
                }catch(e){}
              };
              w.__evRelease = async function(){
                try{ if(w.__evWakeLock){ await w.__evWakeLock.release(); w.__evWakeLock = null; } }catch(e){}
              };
              w.document.addEventListener('visibilitychange', function(){
                if(w.document.visibilityState==='visible' && w.__evWantWake){ w.__evAcquire(); }
              });
            }
            if(w.__evWantWake){ w.__evAcquire(); } else { w.__evRelease(); }
          }catch(e){}
        })();
        </script>""" % flag,
        height=0,
    )

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.info(f"Loaded {len(disposable_domains)} disposable email domains")
    with st.expander("Configuration", expanded=True):
        st.caption("App configuration and settings")

# ── Title ──────────────────────────────────────────────────────────────────────
st.title("Email Validity and Reachability Checker")
st.caption("Validate email addresses with enhanced SMTP server validation.")

# ── Advanced Settings ──────────────────────────────────────────────────────────
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

mode = st.radio("Select Mode", ["Single Email", "Batch (CSV File)"])

SENDER_EMAIL = sender_email


# ── Core logic ─────────────────────────────────────────────────────────────────

def _base_result(email, domain, deliverable, valid, reason, mx, implicit_mx, provider, risky, disposable, accept_all):
    return {
        "email": email,
        "domain": domain,
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


def process_email(email, timeout=7, skip_smtp_check=False, catchall_valid=True):
    domain = email.split("@", 1)[-1].lower() if "@" in email else ""
    is_syntax_valid = validate_email_syntax(email)
    if not is_syntax_valid:
        return _base_result(email, domain, False, False, "Invalid email syntax", None, None, None, False, False, False)

    mx_result = get_mx_record(domain, timeout=timeout)
    mx_record = mx_result[0] if mx_result else None
    implicit_mx = mx_result[1] if mx_result and len(mx_result) > 1 else None

    if not mx_record:
        return _base_result(email, domain, False, False, "MX lookup failed", None, implicit_mx, None, False, False, False)

    is_disposable = domain in disposable_domains
    if is_disposable:
        return _base_result(email, domain, False, False, "Disposable email address", mx_record, implicit_mx, None, False, True, False)

    smtp_provider = get_smtp_provider(domain)

    if skip_smtp_check:
        smtp_deliverable, validation_reason, is_valid = True, "SMTP check skipped", True
    else:
        smtp_deliverable, smtp_reason, is_valid, validation_reason = perform_email_checks(
            target_email=email, sender_email=SENDER_EMAIL,
            disposable_domains=disposable_domains, timeout=timeout,
        )
        if not validation_reason:
            validation_reason = smtp_reason

    has_role = any(r in email.split("@")[0] for r in ["admin", "info", "support", "sales", "contact"])
    is_accept_all = False
    has_no_reply = "no-reply" in email or "noreply" in email

    if catchall_valid and is_accept_all:
        smtp_deliverable = True
        validation_reason = "Catch-all domain treated as valid"

    score, is_risky, _ = evaluate_email_score_and_risk(
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
        "reason": validation_reason,
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


def save_to_db(file_name, emails, results):
    """Returns (file_id, error_message). file_id is None on failure."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        duplicate_count = len(emails) - len(set(emails))
        total = len(results)
        deliverable = sum(1 for r in results if r["is_deliverable"])
        risky = sum(1 for r in results if r["is_risky"])
        deliverable_pct = round((deliverable / total) * 100, 2) if total else 0.0

        bulk = BulkEmailStats(
            user_id=None,  # No FK user needed in Streamlit mode
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
            ) or "N/A"
            implicit = r["implicit_mx_record"]
            te = TestEmail(
                user_id=None,
                file_id=bulk.id,
                user_tested_email=r["email"],
                full_name=full_name,
                gender="Unknown",
                status=r["status"].lower(),
                reason=(r["reason"] or "")[:255],
                domain=r["domain"],
                is_free=False,
                is_risky=bool(r["is_risky"]),
                is_valid=bool(r["is_valid"]),
                is_disposable=bool(r["is_disposable"]),
                is_deliverable=bool(r["is_deliverable"]),
                has_tag=False,
                alphabetical_characters=r["alphabetical_characters"],
                is_mailbox_full=False,
                has_role=bool(r["has_role"]),
                is_accept_all=bool(r["is_accept_all"]),
                has_numerical_characters=r["has_numerical_characters"],
                has_unicode_symbols=r["has_unicode_symbols"],
                has_no_reply=bool(r["has_no_reply"]),
                smtp_provider=str(r["smtp_provider"] or "")[:255],
                mx_record=str(r["mx_record"] or "")[:255],
                implicit_mx_record=str(implicit) if implicit is not None else None,
                score=r["score"],
                soft_delete=False,
                created_at=now,
            )
            db.add(te)

        db.commit()
        return bulk.id, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()


def build_download_df(original_df, email_col, results, status_filter="All"):
    """
    Return the original CSV columns exactly as uploaded, with one 'Status'
    column appended. Rows are filtered by status_filter but never restructured.
    """
    result_map = {r["email"]: r for r in results}

    df = original_df.copy()
    normalized = df[email_col].astype(str).str.strip().str.lower()

    df["Status"] = normalized.map(lambda e: result_map.get(e, {}).get("status", "Unknown"))

    # Temp columns for non-status filters
    df["_risky"] = normalized.map(lambda e: bool(result_map.get(e, {}).get("is_risky", False)))
    df["_deliverable"] = normalized.map(lambda e: bool(result_map.get(e, {}).get("is_deliverable", False)))

    if status_filter == "Valid":
        df = df[df["Status"] == "Valid"]
    elif status_filter == "Invalid":
        df = df[df["Status"] == "Invalid"]
    elif status_filter == "Risky":
        df = df[df["_risky"]]
    elif status_filter == "Deliverable":
        df = df[df["_deliverable"]]

    return df.drop(columns=["_risky", "_deliverable"])


def show_batch_results(results, file_id, db_error, original_df, email_col, task_id, logs):
    """Render metrics, DB status, filter download, and full table. Persists across reruns."""
    total = len(results)
    valid = sum(1 for r in results if r["is_valid"])
    deliverable = sum(1 for r in results if r["is_deliverable"])
    risky = sum(1 for r in results if r["is_risky"])
    invalid = total - valid

    st.divider()
    st.caption(f"Task ID: `{task_id}`")
    st.subheader("Results Summary")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("Valid", valid)
    c3.metric("Deliverable", deliverable)
    c4.metric("Risky", risky)
    c5.metric("Invalid", invalid)

    if file_id:
        st.success(f"Saved to database successfully — File ID: {file_id}")
    else:
        st.error(f"Database save failed: {db_error}")

    st.divider()

    filter_col, _ = st.columns([1, 3])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Valid", "Deliverable", "Invalid", "Risky"],
            key="dl_filter",
        )

    # Build filtered view from the original uploaded sheet
    filtered_df = build_download_df(original_df, email_col, results, status_filter)
    match_count = len(filtered_df)
    st.caption(f"{match_count} row{'s' if match_count != 1 else ''} match '{status_filter}'.")

    # Download button — filtered original sheet + Status column
    if match_count > 0:
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"Download {status_filter} ({match_count} rows)",
            data=csv_bytes,
            file_name=f"results_{status_filter.lower()}.csv",
            mime="text/csv",
            key="dl_btn",
        )
    else:
        st.info("No emails match this filter.")

    # Table also respects the same filter selection
    st.subheader("Results Table")
    st.dataframe(filtered_df, use_container_width=True)

    # Task log panel
    with st.expander(f"Task Logs — {task_id}", expanded=False):
        if logs:
            st.code("\n".join(logs), language=None)
        else:
            st.caption("No logs recorded.")


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
                st.success(f"Valid — {result['reason']}")
            elif result["is_risky"]:
                st.warning(f"Risky — {result['reason']}")
            else:
                st.error(f"Invalid — {result['reason']}")

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
                # Generate unique task ID for this run
                task_id = uuid.uuid4().hex[:10].upper()
                started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                logs = [f"[{started_at}] Task {task_id} started — {len(unique_emails)} unique emails from '{uploaded_file.name}'"]

                # Clear any previous run
                st.session_state.batch_done = False
                st.session_state.batch_results = None
                st.session_state.batch_task_id = task_id
                st.session_state.batch_logs = logs

                st.info(f"Task ID: `{task_id}`")
                progress = st.progress(0)
                status_text = st.empty()
                keep_screen_awake(True)   # acquire lock before long loop
                results = []
                last_domain = None

                for i, email in enumerate(unique_emails):
                    status_text.text(f"[{task_id}] Checking {i + 1}/{len(unique_emails)}: {email}")
                    domain = email.split("@", 1)[-1] if "@" in email else ""

                    if last_domain and domain != last_domain:
                        time.sleep(delay_between_domains)
                    else:
                        time.sleep(delay_between_emails)

                    r = process_email(
                        email,
                        timeout=verification_timeout,
                        skip_smtp_check=skip_smtp,
                        catchall_valid=treat_catchall_valid,
                    )
                    results.append(r)
                    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                    logs.append(f"[{ts}] {email} → {r['status']} | {r['reason']}")
                    last_domain = domain
                    progress.progress((i + 1) / len(unique_emails))

                status_text.text("Saving to database...")
                file_id, db_error = save_to_db(uploaded_file.name, emails, results)

                finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                logs.append(f"[{finished_at}] Task {task_id} complete — DB file_id={file_id or 'ERROR: ' + str(db_error)}")

                # Persist everything in session_state so results survive reruns
                st.session_state.batch_results = results
                st.session_state.batch_file_id = file_id
                st.session_state.batch_db_error = db_error
                st.session_state.batch_done = True
                st.session_state.batch_original_df = df
                st.session_state.batch_email_col = col
                st.session_state.batch_logs = logs

                keep_screen_awake(False)  # release lock — job finished
                progress.empty()
                status_text.text("Validation complete!")

    # Always render results if they exist — survives download button clicks and filter changes
    if st.session_state.batch_done and st.session_state.batch_results:
        keep_screen_awake(False)  # ensure lock is released on every idle re-render
        show_batch_results(
            st.session_state.batch_results,
            st.session_state.batch_file_id,
            st.session_state.batch_db_error,
            st.session_state.batch_original_df,
            st.session_state.batch_email_col,
            st.session_state.batch_task_id,
            st.session_state.batch_logs,
        )
