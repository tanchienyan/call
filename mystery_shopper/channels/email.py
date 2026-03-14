"""Email mystery shopping channel."""

import asyncio
import email
import imaplib
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..config import config
from ..models import Channel, ChannelResult, TestStatus
from ..scoring.engine import score_interaction
from ..scenarios.hotel import get_email_scenario


class EmailMysteryShopperError(Exception):
    pass


class EmailMysteryShopper:
    """Send inquiry emails and score responses."""

    def __init__(self):
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.imap_host = config.IMAP_HOST
        self.imap_user = config.IMAP_USER
        self.imap_password = config.IMAP_PASSWORD

    def send_inquiry(
        self,
        target_email: str,
        subject: str,
        body: str,
        from_name: str = "Sarah Mitchell",
    ) -> ChannelResult:
        """Send a mystery shopping inquiry email."""
        result = ChannelResult(
            channel=Channel.EMAIL,
            status=TestStatus.IN_PROGRESS,
            started_at=datetime.now(),
        )

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{from_name} <{self.smtp_user}>"
            msg["To"] = target_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            result.outbound_content = f"Subject: {subject}\n\n{body}"
            result.status = TestStatus.WAITING_RESPONSE
            print(f"✉️  Email sent to {target_email}")
            return result

        except Exception as e:
            result.status = TestStatus.FAILED
            result.summary = f"Failed to send email: {str(e)}"
            return result

    def check_reply(
        self,
        target_email: str,
        sent_after: datetime,
        timeout_hours: int = 48,
    ) -> tuple[str | None, float | None]:
        """Check for a reply from the target email.

        Returns (reply_content, response_time_seconds) or (None, None).
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host)
            mail.login(self.imap_user, self.imap_password)
            mail.select("inbox")

            # Search for emails from the target
            _, messages = mail.search(None, f'(FROM "{target_email}")')
            if not messages[0]:
                return None, None

            for msg_id in messages[0].split():
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # Parse date
                date_str = msg["Date"]
                # Simple check — just look for any reply after our sent time
                # In production, would do proper date parsing

                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

                if body:
                    response_time = (datetime.now() - sent_after).total_seconds()
                    mail.logout()
                    return body, response_time

            mail.logout()
            return None, None

        except Exception as e:
            print(f"Error checking email: {e}")
            return None, None

    def score_reply(
        self,
        result: ChannelResult,
        reply_content: str,
        response_time_seconds: float,
        criteria: list[dict],
    ) -> ChannelResult:
        """Score the hotel's email reply."""
        result.inbound_content = reply_content
        result.response_time_seconds = response_time_seconds
        result.completed_at = datetime.now()

        scoring = score_interaction(
            channel="email",
            criteria=criteria,
            outbound_content=result.outbound_content,
            inbound_content=reply_content,
            response_time_seconds=response_time_seconds,
        )

        result.scores = scoring["scores"]
        result.overall_score = scoring["overall_score"]
        result.summary = scoring["summary"]
        result.strengths = scoring["strengths"]
        result.improvements = scoring["improvements"]
        result.status = TestStatus.COMPLETED

        return result


def run_email_test(
    target_email: str,
    target_name: str = "Hotel",
    persona_index: int = 0,
    send_only: bool = False,
) -> ChannelResult:
    """Run a complete email mystery shopping test.

    If send_only=True, just sends the email and returns (for async checking later).
    """
    scenario = get_email_scenario(persona_index)
    shopper = EmailMysteryShopper()

    # Send inquiry
    result = shopper.send_inquiry(
        target_email=target_email,
        subject=scenario["subject"],
        body=scenario["body"],
        from_name=scenario["persona"]["name"],
    )

    if send_only or result.status == TestStatus.FAILED:
        return result

    # Wait and check for reply (simplified — in production would be async/webhook)
    print("⏳ Waiting for reply (checking every 30 minutes)...")
    max_checks = 96  # 48 hours
    for i in range(max_checks):
        time.sleep(1800)  # 30 min
        reply, response_time = shopper.check_reply(
            target_email=target_email,
            sent_after=result.started_at,
        )
        if reply:
            print(f"📨 Reply received after {response_time/3600:.1f} hours!")
            return shopper.score_reply(result, reply, response_time, scenario["scoring_criteria"])

    # No reply
    result.status = TestStatus.COMPLETED
    result.overall_score = 0
    result.summary = "No reply received within 48 hours."
    result.improvements = ["Respond to email inquiries — every unanswered email is a lost booking."]
    return result
