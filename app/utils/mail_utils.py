#utils.py 
# this file is handle all main functions of e-mail validator tool
import re
import smtplib
import socket
import ssl
import time
import os
import whois
import dns.resolver
import datetime 
from datetime import timezone
from email.utils import parseaddr
from  typing import Optional, Any

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

    # ✅ WHOIS lookup on the domain only
    dm_info = {}
    try:
        whois_data = whois.whois(domain)
        dm_info['expiration_date'] = getattr(whois_data, 'expiration_date', None)
        dm_info['registrar'] = getattr(whois_data, 'registrar', 'N/A')
        dm_info['creation_date'] = getattr(whois_data, 'creation_date', None)
        dm_info['updated_date'] = getattr(whois_data, 'updated_date', None)
        dm_info['country'] = getattr(whois_data, 'country', 'N/A')
        dm_info['whois_server'] = getattr(whois_data,'whois_server','N/A')
        

        expiration_date = dm_info['expiration_date']
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]

        if expiration_date and expiration_date < datetime.datetime.now(timezone.utc if hasattr(expiration_date, 'tzinfo') and expiration_date.tzinfo else None):
            return False, f"Domain '{domain}' is expired."
    except Exception as e:
        dm_info = {
            'error': f"WHOIS lookup failed: {str(e)}"
        }


    mx_record = get_mx_record(domain)
    if not mx_record:
        return False, f"Domain '{domain}' has no valid MX records"

    if not verify_smtp_server(mx_record, domain):
        return False, f"SMTP server for '{domain}' is not accessible"

    try:
        server = smtplib.SMTP(timeout=2)
        server.set_debuglevel(0)
        server.connect(mx_record, 25)
        server.ehlo_or_helo_if_needed()
        server.mail(sender_email)
        code, message = server.rcpt(address)
        message_str = message.decode('utf-8', 'ignore') if hasattr(message, 'decode') else str(message)

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
        
        
        
        