"""Email channel — send inquiry emails and monitor for replies via IMAP."""

import smtplib
import imaplib
import email as email_lib
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings


PERSONAS = {
    "sarah_mitchell": {
        "name": "Sarah Mitchell",
        "email_style": "professional, concise, warm",
        "subject_templates": [
            "Room Availability Inquiry - {dates}",
            "Booking Inquiry for {dates}",
            "Quick Question About Room Rates",
        ],
    },
    "james_cooper": {
        "name": "James Cooper",
        "email_style": "casual, friendly, slightly verbose",
        "subject_templates": [
            "Planning a Trip - Room Info?",
            "Looking for a Nice Room - {dates}",
        ],
    },
}


async def send_inquiry(
    to_email: str,
    persona_key: str = "sarah_mitchell",
    hotel_name: str = "your hotel",
    dates: str = "next Thursday to Sunday",
    extra_context: str = "",
) -> dict:
    """Send a mystery shopping inquiry email.
    
    Returns dict with: sent (bool), subject, body, error
    """
    persona = PERSONAS.get(persona_key, PERSONAS["sarah_mitchell"])
    name = persona["name"]

    subject = f"Room Availability Inquiry - {dates}"
    body = f"""Dear {hotel_name} Reservations Team,

I hope this email finds you well. My name is {name} and I'm looking to book a room at {hotel_name} from {dates} (3 nights).

I'll be in town for a tech conference and would appreciate a quiet room on a higher floor if available. Could you let me know:

1. What room types are available for those dates?
2. Your best available rates?
3. Is late checkout available (around 2pm)?
4. Do you have a gym and how is the WiFi?

{extra_context}

I'd also be interested in hearing about any current promotions or packages you might have.

Thank you for your time — I look forward to hearing from you.

Best regards,
{name}
bowenzhu790@gmail.com
+1 (201) 231-8503"""

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{name} <{settings.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return {"sent": True, "subject": subject, "body": body, "to": to_email}

    except Exception as e:
        return {"sent": False, "error": str(e), "subject": subject, "body": body}


async def check_replies(
    from_domain: str = "",
    from_address: str = "",
    since_minutes: int = 60 * 24,
) -> list[dict]:
    """Check inbox for replies matching criteria.
    
    Returns list of dicts with: from, subject, body, date
    """
    results = []
    try:
        mail = imaplib.IMAP4_SSL(settings.IMAP_HOST)
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        mail.select("inbox")

        if from_address:
            criteria = f'(FROM "{from_address}")'
        elif from_domain:
            criteria = f'(FROM "@{from_domain}")'
        else:
            criteria = "(UNSEEN)"

        _, messages = mail.search(None, criteria)

        if messages[0]:
            for msg_id in messages[0].split()[-10:]:  # Last 10 matches
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                msg = email_lib.message_from_bytes(msg_data[0][1])

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                results.append({
                    "from": msg.get("From", ""),
                    "subject": msg.get("Subject", ""),
                    "body": body[:2000],
                    "date": msg.get("Date", ""),
                })

        mail.logout()
    except Exception as e:
        return [{"error": str(e)}]

    return results


async def monitor_reply(
    from_domain: str,
    timeout_hours: float = 48,
    check_interval_minutes: float = 15,
    callback=None,
) -> dict:
    """Monitor inbox for a reply, polling at intervals.
    
    Returns dict with: received (bool), reply (dict or None),
    response_time_seconds, checks_made
    """
    import time
    start = time.time()
    timeout_secs = timeout_hours * 3600
    interval_secs = check_interval_minutes * 60
    checks = 0

    while time.time() - start < timeout_secs:
        checks += 1
        replies = await check_replies(from_domain=from_domain)
        real_replies = [r for r in replies if "error" not in r]

        if real_replies:
            elapsed = time.time() - start
            result = {
                "received": True,
                "reply": real_replies[0],
                "response_time_seconds": elapsed,
                "checks_made": checks,
            }
            if callback:
                await callback(result)
            return result

        await asyncio.sleep(interval_secs)

    return {
        "received": False,
        "reply": None,
        "response_time_seconds": timeout_secs,
        "checks_made": checks,
    }
