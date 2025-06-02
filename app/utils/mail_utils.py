# app\utils\mail_utils.py
# this file is handle all main functions of e-mail validator tool
import os
import re
import smtplib
import socket
import ssl
from email.utils import parseaddr
from typing import Optional

import dns.resolver
import whois


def load_disposable_domains(file_path="disposed_email.conf"):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                domains = [line.strip().lower() for line in f if line.strip()]
            return set(domains)
        else:
            return set(["mailinator.com", "tempmail.com", "fakeinbox.com"])
    except:
        return set(["mailinator.com", "tempmail.com", "fakeinbox.com"])


def validate_email_syntax(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def get_mx_record(domain):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 1
        resolver.lifetime = 3
        records = resolver.resolve(domain, "MX")
        if records:
            mx_records = sorted([(r.preference, r.exchange.to_text()) for r in records], key=lambda x: x[0])
            mx_record = mx_records[0][1]
            return mx_record, False  # False = not implicit MX
        return None, True  # Implicit MX
    except:
        return None, True  # No record found or error = implicit MX


def verify_smtp_server(mx_record, domain):
    ports = [25, 587, 465]
    for port in ports:
        try:
            if port == 465:
                context = ssl.create_default_context()
                with socket.create_connection((mx_record, port), timeout=2) as sock:
                    with context.wrap_socket(sock, server_hostname=mx_record):
                        return True
            else:
                with socket.create_connection((mx_record, port), timeout=5):
                    return True
        except:
            continue
    try:
        with socket.create_connection((domain, 25), timeout=2):
            return True
    except:
        return False


def get_smtp_provider(domain: str) -> str:
    provider_map = {
        "gmail.com": "Google",
        "googlemail.com": "Google",
        "yahoo.com": "Yahoo",
        "ymail.com": "Yahoo",
        "outlook.com": "Microsoft",
        "hotmail.com": "Microsoft",
        "live.com": "Microsoft",
        "aol.com": "AOL",
        "icloud.com": "Apple",
        "me.com": "Apple",
        "protonmail.com": "ProtonMail",
        "zoho.com": "Zoho",
        "gmx.com": "GMX",
        "yandex.com": "Yandex",
    }

    domain = domain.lower()
    return provider_map.get(domain, "Unknown")  # Returns provider name or "Unknown"


def check_email_reachability(email, sender_email, disposable_domains):
    # Helper function to analyze characters in email address
    def analyze_string(email):
        alphabetic = sum(1 for c in email if c.isalpha())
        numeric = sum(1 for c in email if c.isdigit())
        symbols = len(email) - alphabetic - numeric
        return {"alphabetic": alphabetic, "numeric": numeric, "symbols": symbols}

    result = analyze_string(email)
    print(result)  # Optional: Debugging output for analysis result

    # Step 1: Syntax Check
    if not validate_email_syntax(email):
        return False, "Invalid email syntax"

    # Step 2: Split the email into local part and domain
    address = parseaddr(email)[1]
    try:
        _, domain = address.split("@")
    except ValueError:
        return False, "Invalid email format"

    # Step 3: Disposable Email Check
    if domain.lower() in disposable_domains:
        return False, "Disposable email address detected"

    # Step 4: WHOIS Lookup
    dm_info = {}
    try:
        whois_data = whois.whois(domain)
        dm_info["registrar"] = getattr(whois_data, "registrar", "N/A")
        dm_info["country"] = getattr(whois_data, "country", "N/A")
        dm_info["whois_server"] = getattr(whois_data, "whois_server", "N/A")
    except Exception as e:
        dm_info = {"error": f"WHOIS lookup failed: {str(e)}"}

    # Step 5: MX Record Check
    mx_record, is_implicit = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records"

    # Step 6: SMTP Server Validation
    if not verify_smtp_server(mx_record, domain):
        return False, f"SMTP server for '{domain}' is not accessible"

    # Step 7: Perform the SMTP verification process

    try:
        server = smtplib.SMTP(timeout=2)
        server.set_debuglevel(0)
        server.connect(mx_record, 25)
        server.ehlo_or_helo_if_needed()
        server.mail(sender_email)
        code, message = server.rcpt(address)
        message_str = message.decode("utf-8", "ignore") if hasattr(message, "decode") else str(message)

        if code == 250:
            return True, "VALID", dm_info
        return False, f"Invalid: SMTP Error {code} - {message_str}", dm_info
    except Exception as e:
        return False, f"SMTP verification failed: {str(e)}", dm_info
    finally:
        try:
            server.quit()
        except:
            pass


def perform_email_checks(target_email: str, sender_email: str, disposable_domains: list):
    # Extract domain and provider
    try:
        domain = target_email.split("@")[1].lower()
    except IndexError:
        return False, "Invalid email format", False, "Invalid email format"

    smtp_provider = get_smtp_provider(domain)

    # Step 1: Perform MX Check (for safety before SMTP)
    mx_record, implicit_mx = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records", False, "MX lookup failed"

    # Step 2: Try verifying SMTP server connection (not email itself)
    smtp_accessible = verify_smtp_server(mx_record, domain)

    # Step 3: Check reachability (full verification including SMTP RCPT TO)
    reachability_result = check_email_reachability(target_email, sender_email, disposable_domains)

    if isinstance(reachability_result, tuple):
        is_deliverable = reachability_result[0]
        validation_reason = reachability_result[1]
    else:
        is_deliverable = reachability_result
        validation_reason = "Reachability check completed."

    # Final Verdict Logic

    # If deliverable via SMTP RCPT check, trust it
    if is_deliverable:
        is_valid = smtp_accessible
        smtp_reason = "SMTP verification passed"

    # Previously you allowed trusted providers to override deliverability — that caused false positives.
    # Now we only allow a small grace period if:
    # - The email was undeliverable
    # - But the provider is known/trusted AND the server is accessible
    elif smtp_provider in {"Google", "Yahoo", "Microsoft"} and smtp_accessible:
        # Optional: Add logic here to detect catch-all domains or retry with different checks
        is_valid = False  # Don't assume validity just because it's Google/Yahoo/etc.
        smtp_reason = "Trusted provider but email not confirmed deliverable"
        validation_reason = f"SMTP accessible for {smtp_provider}, but RCPT check failed"

    # If nothing else passes, mark as invalid
    else:
        is_valid = False
        smtp_reason = "SMTP verification failed"
        validation_reason = "SMTP unreachable or email not deliverable"

    return is_deliverable, smtp_reason, is_valid, validation_reason


def evaluate_email_score_and_risk(
    is_syntax_valid: bool,
    smtp_deliverable: bool,
    is_disposable: bool,
    has_role: bool,
    is_accept_all: bool,
    has_no_reply: bool,
    domain: str,
    mx_record: Optional[str],
    smtp_provider: Optional[str],
):
    score = 0
    tags = []

    if not is_syntax_valid or not smtp_deliverable:
        if not is_syntax_valid:
            tags.append("Invalid syntax")
        if not smtp_deliverable:
            tags.append("SMTP undeliverable")
            if not smtp_provider:
                tags.append("SMTP_not_provider")

        return 0, True, tags

    # 1. Syntax check (10 points)
    if is_syntax_valid:
        score += 10
    else:
        tags.append("Invalid syntax")

    # 2. SMTP deliverability (30 points)
    if smtp_deliverable:
        score += 30
    else:
        tags.append("SMTP undeliverable")

    # 3. Disposable email check (15 points)
    if not is_disposable:
        score += 15
    else:
        tags.append("Disposable domain")

    # 4. Role-based account (10 points)
    if not has_role:
        score += 10
    else:
        tags.append("Role-based email")

    # 5. Accept-all domain (10 points)
    if not is_accept_all:
        score += 10
    else:
        tags.append("Accept-all domain")

    # 6. No-reply address (10 points)
    if not has_no_reply:
        score += 10
    else:
        tags.append("No-reply address")

    # 7. Trusted provider (15 points)
    trusted_providers = ["google", "outlook", "yahoo", "icloud"]
    if smtp_provider and smtp_provider.lower() in trusted_providers:
        score += 15
    else:
        tags.append("Untrusted provider")

    is_risky = score < 60  # mark as risky if score is less than 60

    return score, is_risky, tags
