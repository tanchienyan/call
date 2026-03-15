"""Real journey runner — connects actual channel handlers for live mystery shopping.

Unlike demo_journey.py (simulated data), this module executes real actions:
- Actually browses the hotel website with Playwright
- Actually sends emails via SMTP
- Actually monitors inbox for replies via IMAP
- Actually makes phone calls via Retell AI
- Actually sends WhatsApp messages via wacli
- Runs real sentiment analysis on every interaction
"""

import asyncio
import os
import json
import time
import smtplib
import imaplib
import email as email_lib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .journey import (
    JourneyOrchestrator, JourneyPlan, JourneyStep,
    StepType, StepResult, StepStatus,
)
from ..channels.web_browser import browse_website
from ..channels.phone_retell import phone_call
from ..channels.whatsapp import send_whatsapp, wait_whatsapp
from ..analytics.sentiment import analyze_sentiment, analyze_call_transcript, compare_channel_sentiment
from ..analytics.analyzer import analyze_full_journey, generate_journey_html_report
from ..scenarios.hotel import get_email_scenario
from ..config import config


# ─── Real email handler ───

async def real_send_email(step: JourneyStep, context: dict) -> StepResult:
    """Actually send an inquiry email."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    target_email = step.config.get("to", "")
    persona = context.get("persona", {})
    persona_name = persona.get("name", "Sarah Mitchell")

    # Generate email content using scenario
    scenario = get_email_scenario(0)

    # Inject cross-channel context
    extra_lines = ""
    if context.get("chat_agent_name"):
        extra_lines += f"\nI was chatting with {context['chat_agent_name']} on your website who suggested I email for the best rates.\n"

    subject = scenario["subject"]
    body = scenario["body"]
    if extra_lines:
        body = body.replace("Could you let me know", extra_lines + "\nCould you let me know")

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{persona_name} <{config.SMTP_USER}>"
        msg["To"] = target_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)

        result.status = StepStatus.COMPLETED
        result.data_sent = f"Subject: {subject}\n\n{body}"
        result.notes = f"Email sent to {target_email} as {persona_name}"
        print(f"   ✅ Email sent to {target_email}")

    except Exception as e:
        result.status = StepStatus.FAILED
        result.notes = f"Failed to send: {e}"
        print(f"   ❌ Failed: {e}")

    result.completed_at = datetime.now()
    return result


async def real_wait_email(step: JourneyStep, context: dict) -> StepResult:
    """Monitor inbox for a reply from the target."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    target_email_domain = step.config.get("from_domain", "")
    from_address = step.config.get("from_address", "")
    timeout_hours = step.config.get("timeout_hours", 48)
    check_interval = step.config.get("check_interval_minutes", 30)

    print(f"   📨 Monitoring inbox for reply from {from_address or target_email_domain}...")
    print(f"   ⏰ Will check every {check_interval} minutes for up to {timeout_hours} hours")

    start_time = time.time()
    timeout_seconds = timeout_hours * 3600
    checks = 0

    while time.time() - start_time < timeout_seconds:
        checks += 1
        try:
            mail = imaplib.IMAP4_SSL(config.IMAP_HOST)
            mail.login(config.IMAP_USER, config.IMAP_PASSWORD)
            mail.select("inbox")

            search_criteria = f'(FROM "{from_address}")' if from_address else "(UNSEEN)"
            _, messages = mail.search(None, search_criteria)

            if messages[0]:
                for msg_id in messages[0].split():
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    msg = email_lib.message_from_bytes(msg_data[0][1])

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
                        elapsed = time.time() - start_time
                        result.status = StepStatus.COMPLETED
                        result.data_received = body
                        result.response_time_seconds = elapsed
                        result.completed_at = datetime.now()

                        hours = elapsed / 3600
                        result.notes = f"Reply received after {hours:.1f} hours"
                        print(f"   📨 Reply received after {hours:.1f} hours!")

                        # Run sentiment analysis on the reply
                        try:
                            sentiment = analyze_sentiment(body, channel="email",
                                context=f"Reply to a hotel booking inquiry from {context.get('persona', {}).get('name', 'a guest')}")
                            result.scores["sentiment"] = sentiment
                            result.scores["overall"] = _sentiment_to_score(sentiment)
                            print(f"   🧠 Sentiment: {sentiment.get('sentiment', 'N/A')} ({sentiment.get('sentiment_score', 0):.2f})")
                            print(f"   🧠 Tone: {sentiment.get('tone_description', 'N/A')}")
                        except Exception as e:
                            print(f"   ⚠️ Sentiment analysis failed: {e}")

                        mail.logout()
                        return result

            mail.logout()

        except Exception as e:
            if checks == 1:
                print(f"   ⚠️ IMAP error: {e}")

        elapsed_hours = (time.time() - start_time) / 3600
        if checks <= 3 or checks % 10 == 0:
            print(f"   ⏳ No reply yet ({elapsed_hours:.1f}h elapsed)")

        await asyncio.sleep(check_interval * 60)

    # Timeout
    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = timeout_seconds
    result.scores = {"overall": 0}
    result.notes = f"No reply received within {timeout_hours} hours"
    print(f"   ❌ No reply after {timeout_hours} hours")
    return result


# ─── Real webchat handler (Playwright) ───

async def real_webchat(step: JourneyStep, context: dict) -> StepResult:
    """Actually interact with a hotel's webchat widget."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    url = context.get("target", {}).get("website", "")
    message = step.config.get("message", "Hi, I'm interested in booking a room.")

    if not url:
        result.status = StepStatus.SKIPPED
        result.notes = "No website URL available"
        return result

    if not context.get("has_chat"):
        result.status = StepStatus.SKIPPED
        result.notes = "No chat widget detected on website"
        return result

    print(f"   💬 Attempting webchat on {url}...")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Try common chat widget selectors
            chat_triggers = [
                "[class*='chat-trigger']", "[class*='chat-button']",
                "[class*='livechat-button']", "[id*='chat-widget']",
                "button[aria-label*='chat']", "[class*='intercom-launcher']",
                "[class*='drift-widget']", "[class*='tawk-button']",
            ]

            chat_opened = False
            for sel in chat_triggers:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        chat_opened = True
                        print(f"   💬 Chat widget opened")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    pass

            if chat_opened:
                # Try to type in chat
                chat_inputs = [
                    "textarea[class*='chat']", "input[class*='chat']",
                    "[contenteditable='true']", "textarea[placeholder*='message']",
                ]
                for sel in chat_inputs:
                    try:
                        inp = await page.query_selector(sel)
                        if inp:
                            await inp.fill(message)
                            await page.keyboard.press("Enter")
                            print(f"   💬 Message sent: {message[:60]}...")
                            result.data_sent = message

                            # Wait for response
                            await asyncio.sleep(10)
                            ss_path = f"data/screenshots/webchat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            os.makedirs("data/screenshots", exist_ok=True)
                            await page.screenshot(path=ss_path)
                            result.screenshots.append(ss_path)
                            break
                    except Exception:
                        pass

                result.status = StepStatus.COMPLETED
                result.notes = "Webchat interaction attempted"
            else:
                result.status = StepStatus.FAILED
                result.notes = "Could not open chat widget"

            await browser.close()

    except ImportError:
        result.status = StepStatus.FAILED
        result.notes = "Playwright not installed"
    except Exception as e:
        result.status = StepStatus.FAILED
        result.notes = str(e)

    result.completed_at = datetime.now()
    return result


# ─── Follow-up monitor ───

async def real_wait_followup(step: JourneyStep, context: dict) -> StepResult:
    """Monitor all channels for proactive follow-up from the hotel."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    timeout_hours = step.config.get("timeout_hours", 72)
    check_interval = 60 * 60  # Check every hour

    print(f"   ⏳ Monitoring for proactive follow-up ({timeout_hours}h)...")

    start_time = time.time()
    timeout_seconds = timeout_hours * 3600

    while time.time() - start_time < timeout_seconds:
        # Check email
        try:
            mail = imaplib.IMAP4_SSL(config.IMAP_HOST)
            mail.login(config.IMAP_USER, config.IMAP_PASSWORD)
            mail.select("inbox")
            _, messages = mail.search(None, "(UNSEEN)")
            if messages[0]:
                elapsed = time.time() - start_time
                result.status = StepStatus.COMPLETED
                result.response_time_seconds = elapsed
                result.scores = {"overall": max(80 - int(elapsed / 3600) * 5, 20)}
                result.notes = f"Follow-up received after {elapsed/3600:.1f} hours"
                print(f"   ✅ Follow-up detected after {elapsed/3600:.1f}h!")
                mail.logout()
                result.completed_at = datetime.now()
                return result
            mail.logout()
        except Exception:
            pass

        elapsed_hours = (time.time() - start_time) / 3600
        day = int(elapsed_hours / 24) + 1
        if int(elapsed_hours) % 24 == 0 and elapsed_hours > 1:
            print(f"   ⏳ Day {day}: No follow-up yet")

        await asyncio.sleep(check_interval)

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = timeout_seconds
    result.scores = {"overall": 0}
    result.notes = f"No follow-up received in {timeout_hours} hours"
    print(f"   ❌ No follow-up after {timeout_hours}h")
    return result


# ─── Analysis step ───

async def real_analyze(step: JourneyStep, context: dict) -> StepResult:
    """Run full analysis with sentiment comparison across channels."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())
    print(f"   📊 Running cross-channel analysis...")

    # Collect sentiment analyses from each channel
    channel_sentiments = {}
    step_results = context.get("step_results", {})
    for name, sr in step_results.items():
        if hasattr(sr, 'scores') and isinstance(sr.scores, dict) and 'sentiment' in sr.scores:
            channel_sentiments[name] = sr.scores['sentiment']

    # Run cross-channel comparison if we have multiple channels
    if len(channel_sentiments) >= 2:
        try:
            comparison = compare_channel_sentiment(channel_sentiments)
            result.scores["cross_channel"] = comparison
            print(f"   🔄 Cross-channel consistency: {comparison.get('consistency_score', 'N/A')}/100")
        except Exception as e:
            print(f"   ⚠️ Cross-channel analysis failed: {e}")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.notes = "Analysis complete"
    return result


# ─── Helpers ───

def _sentiment_to_score(sentiment: dict) -> int:
    """Convert sentiment analysis to a 0-100 score."""
    score = 50  # baseline

    # Sentiment score (-1 to 1) → 0-30 points
    sent_score = sentiment.get("sentiment_score", 0)
    score += int(sent_score * 30)

    # Hospitality markers → 0-20 points
    markers = sentiment.get("hospitality_markers", {})
    marker_count = sum(1 for v in markers.values() if v)
    score += int(marker_count / max(len(markers), 1) * 20)

    return max(0, min(100, score))


# ─── Main runner ───

async def run_real_journey(
    target_name: str,
    target_website: str,
    target_email: str = "",
    target_phone: str = "",
    target_whatsapp: str = "",
) -> dict:
    """Execute a real mystery shopping journey against an actual hotel."""

    orch = JourneyOrchestrator()

    # Register REAL handlers
    orch.register_channel(StepType.BROWSE_WEBSITE, browse_website)
    orch.register_channel(StepType.WEBCHAT, real_webchat)
    orch.register_channel(StepType.SEND_EMAIL, real_send_email)
    orch.register_channel(StepType.WAIT_EMAIL, real_wait_email)
    orch.register_channel(StepType.PHONE_CALL, phone_call)
    orch.register_channel(StepType.SEND_WHATSAPP, send_whatsapp)
    orch.register_channel(StepType.WAIT_WHATSAPP, wait_whatsapp)
    orch.register_channel(StepType.WAIT_FOLLOWUP, real_wait_followup)
    orch.register_channel(StepType.ANALYZE, real_analyze)

    # Build journey plan
    plan = JourneyPlan.hotel_full_journey(
        target_name=target_name,
        target_website=target_website,
        target_email=target_email,
        target_phone=target_phone,
        target_whatsapp=target_whatsapp,
    )

    # Execute
    results = await orch.execute(plan)
    journey_report = orch.get_journey_report()

    # Full journey LLM analysis
    analysis = None
    try:
        if config.OPENAI_API_KEY:
            print("\n📊 Running full journey AI analysis...")
            analysis = analyze_full_journey(journey_report)
    except Exception as e:
        print(f"   ⚠️ Analysis error: {e}")

    # Generate report
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if analysis:
        html = generate_journey_html_report(journey_report, analysis, target_name)
        html_path = f"data/journey_real_{timestamp}.html"
        with open(html_path, "w") as f:
            f.write(html)
        print(f"\n🌐 Report saved: {html_path}")

    json_path = f"data/journey_real_{timestamp}.json"
    full_data = {"journey": journey_report, "analysis": analysis}
    with open(json_path, "w") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"📄 JSON saved: {json_path}")

    return full_data
