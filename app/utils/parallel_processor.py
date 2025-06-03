from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Set
import asyncio
from app.utils.mail_utils import (
    validate_email_syntax,
    get_mx_record,
    perform_email_checks,
    get_smtp_provider,
    evaluate_email_score_and_risk,
)
import re
import dns.resolver
import aiosmtplib
import socket
from functools import lru_cache
import async_timeout

# Configuration
SMTP_TIMEOUT = 5  # seconds
DNS_TIMEOUT = 2   # seconds
MAX_CONCURRENT_CHECKS = 20
CACHE_SIZE = 1000

# Connection pool for SMTP connections
smtp_connection_pool = {}

@lru_cache(maxsize=CACHE_SIZE)
async def get_mx_records_async(domain: str) -> tuple:
    """Cached MX record lookup with timeout"""
    try:
        async with async_timeout.timeout(DNS_TIMEOUT):
            resolver = dns.resolver.Resolver()
            resolver.timeout = DNS_TIMEOUT
            resolver.lifetime = DNS_TIMEOUT
            mx_records = resolver.resolve(domain, 'MX')
            records = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
            return records[0][1] if records else None, None
    except asyncio.TimeoutError:
        return None, "DNS lookup timeout"
    except Exception:
        return None, "DNS lookup failed"

async def check_smtp_async(email: str, domain: str, mx_host: str) -> tuple:
    """Async SMTP check with connection pooling and timeout"""
    try:
        async with async_timeout.timeout(SMTP_TIMEOUT):
            # Use connection from pool or create new one
            if domain in smtp_connection_pool:
                smtp = smtp_connection_pool[domain]
            else:
                smtp = aiosmtplib.SMTP(hostname=mx_host, port=25, timeout=SMTP_TIMEOUT)
                smtp_connection_pool[domain] = smtp

            try:
                await smtp.connect()
                await smtp.ehlo()
                _, response = await smtp.mail('')
                _, response = await smtp.rcpt(email)
                return True, "Email exists"
            except aiosmtplib.SMTPRecipientRefused:
                return False, "Invalid recipient"
            except Exception as e:
                return False, str(e)
            finally:
                try:
                    await smtp.quit()
                except:
                    pass
    except asyncio.TimeoutError:
        return False, "SMTP check timeout"
    except Exception as e:
        return False, f"SMTP check failed: {str(e)}"

async def process_email_async(email: str, disposable_domains: Set[str]) -> Dict[str, Any]:
    """Process a single email asynchronously"""
    try:
        # Basic validation
        is_syntax_valid = validate_email_syntax(email)
        if not is_syntax_valid:
            return {
                "user_tested_email": email,
                "status": "invalid",
                "reason": "Invalid email syntax",
                "is_valid": False,
                "is_deliverable": False,
                "is_risky": True,  # Add is_risky for invalid syntax
                "score": 0,
                "domain": email.split("@", 1)[-1].lower() if "@" in email else "",
                "full_name": "N/A",
                "gender": "Unknown",
                "is_free": False,
                "is_disposable": False,
                "has_tag": False,
                "is_mailbox_full": False,
                "has_role": False,
                "is_accept_all": False,
                "has_no_reply": False,
                "smtp_provider": "",
                "mx_record": "",
                "implicit_mx_record": None
            }

        # Extract domain
        domain = email.split("@", 1)[-1].lower()
        is_disposable = domain in disposable_domains

        # Async MX lookup
        mx_record, mx_error = await get_mx_records_async(domain)
        if not mx_record:
            return {
                "user_tested_email": email,
                "status": "invalid",
                "reason": mx_error or "No MX record found",
                "is_valid": False,
                "is_deliverable": False,
                "is_risky": True,  # Add is_risky for MX record failure
                "score": 0,
                "domain": domain,
                "full_name": "N/A",
                "gender": "Unknown",
                "is_free": False,
                "is_disposable": is_disposable,
                "has_tag": False,
                "is_mailbox_full": False,
                "has_role": False,
                "is_accept_all": False,
                "has_no_reply": False,
                "smtp_provider": "",
                "mx_record": "",
                "implicit_mx_record": None
            }

        # Async SMTP check
        smtp_deliverable, smtp_reason = await check_smtp_async(email, domain, mx_record)

        # Process other attributes
        match = re.search(r"@([a-zA-Z0-9.-]+)", email)
        domain_name = match.group(1) if match else "unknown"
        
        local_part = re.sub(r"[^a-zA-Z._-]", "", email.split("@", 1)[0])
        cleaned_name = re.sub(r"[\\._-]+", " ", local_part).strip()
        full_name = " ".join(part.capitalize() for part in cleaned_name.split()) or "N/A"

        # Quick attribute calculations
        has_role = any(role in email for role in ["admin", "info", "support", "sales", "contact"])
        is_accept_all = "accept" in email or "all" in email
        has_no_reply = "no-reply" in email or "noreply" in email
        smtp_provider = get_smtp_provider(domain)

        # Risk evaluation
        score, is_risky, _ = evaluate_email_score_and_risk(
            is_syntax_valid=is_syntax_valid,
            smtp_deliverable=smtp_deliverable,
            is_disposable=is_disposable,
            has_role=has_role,
            is_accept_all=is_accept_all,
            has_no_reply=has_no_reply,
            domain=domain,
            mx_record=mx_record,
            smtp_provider=smtp_provider
        )

        return {
            "user_tested_email": email,
            "full_name": full_name,
            "gender": "Unknown",
            "status": "valid" if smtp_deliverable else "invalid",
            "reason": smtp_reason,
            "domain": domain_name,
            "is_free": False,
            "is_risky": is_risky,  # Ensure is_risky is included
            "is_valid": smtp_deliverable,
            "is_disposable": is_disposable,
            "is_deliverable": smtp_deliverable,
            "has_tag": False,
            "is_mailbox_full": False,
            "has_role": has_role,
            "is_accept_all": is_accept_all,
            "has_no_reply": has_no_reply,
            "smtp_provider": smtp_provider,
            "mx_record": mx_record or "",
            "implicit_mx_record": None,
            "score": score
        }
    except Exception as e:
        print(f"Error processing email {email}: {str(e)}")
        # Return a default error response with all required fields
        return {
            "user_tested_email": email,
            "status": "error",
            "reason": str(e),
            "is_valid": False,
            "is_deliverable": False,
            "is_risky": True,  # Add is_risky for error cases
            "score": 0,
            "domain": email.split("@", 1)[-1].lower() if "@" in email else "",
            "full_name": "N/A",
            "gender": "Unknown",
            "is_free": False,
            "is_disposable": False,
            "has_tag": False,
            "is_mailbox_full": False,
            "has_role": False,
            "is_accept_all": False,
            "has_no_reply": False,
            "smtp_provider": "",
            "mx_record": "",
            "implicit_mx_record": None
        }

async def cleanup_connection_pool():
    """Cleanup and close all SMTP connections in the pool"""
    for domain, smtp in smtp_connection_pool.items():
        try:
            await smtp.quit()
        except:
            pass
    smtp_connection_pool.clear()

async def process_emails_optimized(
    emails: List[str],
    disposable_domains: Set[str],
    chunk_size: int = 50,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """Main function to process emails in optimized chunks"""
    try:
        all_results = []
        chunks = [emails[i:i + chunk_size] for i in range(0, len(emails), chunk_size)]
        
        for chunk in chunks:
            chunk_results = await process_emails_chunk(
                emails=chunk,
                disposable_domains=disposable_domains,
                chunk_size=chunk_size,
                progress_callback=progress_callback
            )
            all_results.extend(chunk_results)
            
            # Small delay between chunks to prevent resource exhaustion
            await asyncio.sleep(0.1)
        
        return all_results
    finally:
        # Cleanup connection pool after processing
        await cleanup_connection_pool()

async def process_emails_chunk(
    emails: List[str],
    disposable_domains: Set[str],
    chunk_size: int = 50,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """Process a chunk of emails with concurrency control"""
    tasks = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    
    async def process_with_semaphore(email):
        async with semaphore:
            try:
                async with async_timeout.timeout(SMTP_TIMEOUT * 2):  # Double timeout for entire process
                    return await process_email_async(email, disposable_domains)
            except asyncio.TimeoutError:
                print(f"Timeout processing email: {email}")
                return None
            except Exception as e:
                print(f"Error processing email {email}: {str(e)}")
                return None
    
    for email in emails:
        tasks.append(process_with_semaphore(email))
    
    results = []
    for i, task in enumerate(asyncio.as_completed(tasks)):
        try:
            result = await task
            if result:
                results.append(result)
            
            if progress_callback:
                progress = int((i + 1) / len(emails) * 100)
                await progress_callback(progress, i + 1, len(emails))
        except Exception as e:
            print(f"Task error: {str(e)}")
            continue
    
    return results 