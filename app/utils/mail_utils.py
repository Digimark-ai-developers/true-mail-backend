#utils.py 
# this file is handle all main functions of e-mail validator tool
import re
import smtplib
import socket
import ssl
import time
import os
import dns.resolver
from email.utils import parseaddr


def load_disposable_domains(file_path='disposed_email.conf'):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                domains = [line.strip().lower() for line in f if line.strip()]
            return set(domains)
        else:
            return set(['mailinator.com', 'tempmail.com', 'fakeinbox.com'])
    except:
        return set(['mailinator.com', 'tempmail.com', 'fakeinbox.com'])


def validate_email_syntax(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_mx_record(domain):
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 1
        resolver.lifetime = 3
        records = resolver.resolve(domain, 'MX')
        if records:
            mx_records = sorted([(r.preference, r.exchange.to_text()) for r in records], key=lambda x: x[0])
            return mx_records[0][1]
        return None
    except:
        return None


def verify_smtp_server(mx_record, domain):
    ports = [25, 587, 465]
    for port in ports:
        try:
            if port == 465:
                context = ssl.create_default_context()
                with socket.create_connection((mx_record, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=mx_record):
                        return True
            else:
                with socket.create_connection((mx_record, port), timeout=5):
                    return True
        except:
            continue
    try:
        with socket.create_connection((domain, 25), timeout=5):
            return True
    except:
        return False
    


def check_email_reachability(email, sender_email, disposable_domains):
    if not validate_email_syntax(email):
        return False, "Invalid email syntax"

    address = parseaddr(email)[1]
    try:
        _, domain = address.split('@')
    except ValueError:
        return False, "Invalid email format"

    if domain.lower() in disposable_domains:
        return False, "Disposable email address detected"

    mx_record = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records"

    if not verify_smtp_server(mx_record, domain):
        return False, f"SMTP server for '{domain}' is not accessible"

    try:
        server = smtplib.SMTP(timeout=7)
        server.set_debuglevel(0)
        server.connect(mx_record, 25)
        server.ehlo_or_helo_if_needed()
        server.mail(sender_email)
        code, message = server.rcpt(address)
        message_str = message.decode('utf-8', 'ignore') if hasattr(message, 'decode') else str(message)
        if code == 250:
            return True, "VALID"
        return False, f"Invalid: SMTP Error {code} - {message_str}"
    except Exception as e:
        return False, f"SMTP verification failed: {str(e)}"
    finally:
        try:
            server.quit()
        except:
            pass
