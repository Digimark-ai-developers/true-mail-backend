# app\utils\mail_utils.py
# this file handles all main functions of the email validator tool
import os
import re
import smtplib
import socket
import ssl
import threading
import time
from collections import defaultdict
from email.utils import parseaddr
from typing import Optional

import dns.resolver
import whois

CACHE_TTL = 600
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
GLOBAL_MAX_CALLS = 100  # Max global calls
GLOBAL_PERIOD = 60  # per 60 seconds
DOMAIN_MAX_CALLS = 5
DOMAIN_PERIOD = 60

# Configure DNS resolver
resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = ["8.8.8.8", "98.138.11.157", "98.139.11.157"]
resolver.cache = dns.resolver.Cache()

# Domain rate limit tracking
domain_call_times = defaultdict(list)
domain_locks = {}


def get_domain_lock(domain):
    if domain not in domain_locks:
        domain_locks[domain] = threading.Lock()
    return domain_locks[domain]


def rate_limit_domain(domain, max_calls=DOMAIN_MAX_CALLS, period=DOMAIN_PERIOD):
    now = time.time()
    lock = get_domain_lock(domain)

    with lock:
        call_times = domain_call_times[domain]
        call_times[:] = [t for t in call_times if t > now - period]
        if len(call_times) >= max_calls:
            wait_time = call_times[0] + period - now
            time.sleep(wait_time)
            call_times[:] = [t for t in call_times if t > now - period]
        call_times.append(time.time())


def rate_limited_call(calls_per_period, period_seconds):
    def decorator(func):
        calls = []

        def wrapper(*args, **kwargs):
            now = time.time()
            with threading.Lock():
                calls[:] = [t for t in calls if t > now - period_seconds]
                if len(calls) >= calls_per_period:
                    sleep_time = calls[0] + period_seconds - now
                    time.sleep(sleep_time)
            calls.append(now)
            return func(*args, **kwargs)

        return wrapper

    return decorator


@rate_limited_call(GLOBAL_MAX_CALLS, GLOBAL_PERIOD)
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
    pattern = r"^[a-zA-Z0-8._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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
    ports = [587, 465, 25]  # Try secure ports first
    for port in ports:
        try:
            if port == 465:
                context = ssl.create_default_context()
                with socket.create_connection((mx_record, port), timeout=1.5) as sock:
                    with context.wrap_socket(sock, server_hostname=mx_record):
                        return True
            else:
                with socket.create_connection((mx_record, port), timeout=1.5) as sock:
                    s = smtplib.SMTP()
                    s.sock = sock
                    s.file = s.sock.makefile("rb")
                    code, _ = s.getreply()
                    if code != 220:
                        continue
                    s.helo()
                    if s.has_extn("starttls"):
                        s.starttls()
                    s.quit()
                    return True
        except Exception as e:
            print(f"An error occurred: {e}")
            continue
    try:
        with socket.create_connection((domain, 25), timeout=1.5):
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
    return provider_map.get(domain, "Unknown")


def check_email_reachability(email, sender_email, disposable_domains):
    def analyze_string(email):
        alphabetic = sum(1 for c in email if c.isalpha())
        numeric = sum(1 for c in email if c.isdigit())
        symbols = len(email) - alphabetic - numeric
        return {"alphabetic": alphabetic, "numeric": numeric, "symbols": symbols}

    # result = analyze_string(email)

    if not validate_email_syntax(email):
        return False, "Invalid email syntax"

    address = parseaddr(email)[1]
    try:
        _, domain = address.split("@")
    except ValueError:
        return False, "Invalid email format"

    if domain.lower() in disposable_domains:
        return False, "Disposable email address detected"

    dm_info = {}
    try:
        whois_data = whois.whois(domain)
        dm_info["registrar"] = getattr(whois_data, "registrar", "N/A")
        dm_info["country"] = getattr(whois_data, "country", "N/A")
        dm_info["whois_server"] = getattr(whois_data, "whois_server", "N/A")
    except Exception as e:
        dm_info = {"error": f"WHOIS lookup failed: {str(e)}"}

    TRUSTED_DOMAINS = {"yahoo.com", "ymail.com", "gmail.com", "googlemail.com", "outlook.com"}
    if domain in TRUSTED_DOMAINS:
        mx_record, is_implicit = get_mx_record(domain)
        if not mx_record:
            return False, f"No MX record found for {domain}"
        dm_info["note"] = f"{domain} blocks RCPT checks"
        return True, "VALID", dm_info

    mx_record, is_implicit = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records"

    if not verify_smtp_server(mx_record, domain):
        return False, f"SMTP server for '{domain}' is not accessible"

    try:
        server = smtplib.SMTP(timeout=5)
        server.set_debuglevel(0)
        server.connect(mx_record, 25)
        server.ehlo_or_helo_if_needed()

        if server.has_extn("STARTTLS"):
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()

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
    try:
        domain = target_email.split("@")[1].lower()
    except IndexError:
        return False, "Invalid email format", False, "Invalid email format"

    rate_limit_domain(domain)

    smtp_provider = get_smtp_provider(domain)

    mx_record, implicit_mx = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records", False, "MX lookup failed"

    smtp_accessible = verify_smtp_server(mx_record, domain)

    reachability_result = check_email_reachability(target_email, sender_email, disposable_domains)

    if isinstance(reachability_result, tuple):
        is_deliverable = reachability_result[0]
        validation_reason = reachability_result[1]
    else:
        is_deliverable = reachability_result
        validation_reason = "Reachability check completed."

    if is_deliverable:
        is_valid = smtp_accessible
        smtp_reason = "SMTP verification passed"
    elif smtp_provider in {"Google", "Yahoo", "Microsoft"} and smtp_accessible:
        is_valid = True
        smtp_reason = "Trusted provider overrides undeliverable status"
        validation_reason = f"{smtp_provider} blocks RCPT checks but MX exists"
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

    if is_syntax_valid:
        score += 10
    else:
        tags.append("Invalid syntax")

    if smtp_deliverable:
        score += 30
    else:
        tags.append("SMTP undeliverable")

    if not is_disposable:
        score += 15
    else:
        tags.append("Disposable domain")

    if not has_role:
        score += 10
    else:
        tags.append("Role-based email")

    if not is_accept_all:
        score += 10
    else:
        tags.append("Accept-all domain")

    if not has_no_reply:
        score += 10
    else:
        tags.append("No-reply address")

    trusted_providers = ["google", "outlook", "yahoo", "icloud"]
    if smtp_provider and smtp_provider.lower() in trusted_providers:
        score += 15
    else:
        tags.append("Untrusted provider")

    is_risky = score < 60

    return score, is_risky, tags
