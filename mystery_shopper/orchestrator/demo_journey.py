"""Demo journey — simulates a full multi-channel mystery shopping experience.

Run without any API keys to see what the full product looks like.
"""

import asyncio
import os
import json
import time
from datetime import datetime, timedelta

from .journey import (
    JourneyOrchestrator, JourneyPlan, JourneyStep,
    StepType, StepResult, StepStatus,
)
from ..analytics.analyzer import analyze_full_journey, generate_journey_html_report


# ─── Simulated channel handlers for demo ───


async def demo_browse(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())
    url = step.config.get("url", "https://www.grandhotel.com")

    print(f"   🌐 Browsing {url}...")
    time.sleep(1)
    print(f"   📸 Screenshot: homepage captured")
    time.sleep(0.5)
    print(f"   📸 Screenshot: rooms page captured")
    time.sleep(0.5)
    print(f"   💬 Live chat widget: ✅ Found (Intercom)")
    print(f"   📅 Booking widget: ✅ Found")
    print(f"   📋 Found 4 room types, rates from £189-£449/night")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.data_received = "Homepage, Rooms page, About page browsed. 4 room types found."
    result.screenshots = ["data/demo/homepage.png", "data/demo/rooms.png"]
    result.context_for_next = {
        "has_chat": True,
        "has_booking": True,
        "room_types": ["Superior", "Executive", "Junior Suite", "Presidential Suite"],
        "rate_range": "£189-£449",
    }
    result.scores = {"overall": 78}
    result.notes = "Good website with booking widget and live chat. Room info could be more detailed."
    return result


async def demo_webchat(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   💬 Opening webchat...")
    time.sleep(0.5)
    print(f"   💬 Sending: 'Hi, looking for a quiet room next Thu-Sun...'")
    time.sleep(1.5)
    print(f"   💬 Agent replied in 45 seconds")
    print(f"   💬 Asking about rates...")
    time.sleep(1)
    print(f"   💬 Agent provided rate range but suggested emailing for best offer")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = 45
    result.data_sent = "Hi, I'm looking for a quiet room on a high floor, next Thursday to Sunday. Do you have availability?"
    result.data_received = """Agent: Hi Sarah! Welcome to The Grand Hotel. Yes, we do have availability for those dates! 
For a quiet high-floor room, I'd recommend our Executive Room on the 8th floor. 
Rates start from £249/night. Would you like me to check exact availability?
I can also have our reservations team email you a detailed quote with any special offers we have running. 
Could I get your email address?"""
    result.scores = {"overall": 72}
    result.notes = "Good response time (45s). Provided room suggestion. But redirected to email instead of closing on chat."
    result.context_for_next = {"chat_agent_name": "Sophie", "provided_email": True}
    return result


async def demo_send_email(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   📧 Sending inquiry email to {step.config.get('to', 'hotel')}...")
    time.sleep(0.5)
    print(f"   ✅ Email sent!")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.data_sent = """Subject: Room availability inquiry - next Thursday to Sunday

Hi there,

I'm looking to book a stay at your hotel:
- Dates: next Thursday to Sunday (3 nights)  
- Guests: 1 adult
- Room preference: quiet room, high floor
- Purpose: attending a tech conference nearby
- Interested in: late checkout, gym/wifi

I was chatting with Sophie on your website who suggested I email for the best rates.

Could you let me know about availability and rates?

Best regards,
Sarah Mitchell"""
    result.notes = "Email sent successfully. Referenced webchat conversation for cross-channel continuity."
    return result


async def demo_wait_email(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   📨 Waiting for email reply...")
    time.sleep(1)
    print(f"   ⏳ Checking... no reply after 2 hours")
    time.sleep(0.5)
    print(f"   ⏳ Checking... no reply after 4 hours")
    time.sleep(0.5)
    print(f"   📨 Reply received after 6.5 hours!")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = 6.5 * 3600
    result.data_received = """Dear Sarah,

Thank you for your interest in The Grand Hotel.

I can confirm availability for next Thursday to Sunday (3 nights). Here are our options:

- Superior Room (7th floor): £199/night
- Executive Room (8th floor, recommended): £259/night — includes lounge access and breakfast
- Junior Suite (9th floor): £349/night

WiFi is complimentary in all rooms, and our gym is open 24/7.

Late checkout can usually be arranged until 2pm subject to availability.

Please let me know if you'd like to proceed with a booking.

Kind regards,
Maria Garcia
Reservations Team"""
    result.scores = {"overall": 58}
    result.notes = "Took 6.5 hours to reply (should be under 4). Good content but no mention of conference deal, no direct booking link, no urgency. Didn't reference the webchat conversation."
    return result


async def demo_phone_call(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   📞 Calling {step.config.get('phone_number', 'hotel')}...")
    time.sleep(0.5)
    print(f"   📞 Ringing...")
    time.sleep(1)
    print(f"   📞 Connected! Call in progress...")
    time.sleep(2)
    print(f"   📞 Call completed (2m 45s)")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = 165
    result.data_sent = "AI called as Sarah Mitchell, referencing previous email"
    result.data_received = """[Ring x4]
Hotel: Grand Hotel, good afternoon, how can I help?
Sarah: Hi, I sent an email earlier about booking a room for next Thursday to Sunday. I just wanted to follow up and ask a couple more questions.
Hotel: Of course. Let me see... ah yes, I can see your email. The Executive Room, was it?
Sarah: Yes, that one looked good. I'm attending a conference nearby — do you have any conference rates or deals?
Hotel: Um, I'm not sure about specific conference rates. I'd have to check with my manager on that. The £259 is already quite competitive.
Sarah: Okay. And the late checkout — can that be guaranteed?
Hotel: We can note it on the reservation but it's subject to availability on the day, I'm afraid.
Sarah: That's fine. One more thing — is the gym well-equipped? I like to run in the mornings.
Hotel: Yes, we have treadmills and weights. It's on the ground floor. Open 24 hours.
Sarah: Lovely. Could you email me a summary with a booking link? I'll confirm later today.
Hotel: Sure, I'll send that over. Is it the same email?
Sarah: Yes, sarah@email.com. Thank you!
Hotel: Thank you, have a lovely day."""
    result.scores = {"overall": 65}
    result.notes = "Answered in 4 rings (acceptable). Knew about the email (good cross-channel). But didn't know about conference rates, couldn't guarantee late checkout, didn't proactively upsell. No mention of direct booking benefits."
    return result


async def demo_whatsapp(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   📱 Sending WhatsApp message...")
    time.sleep(0.5)
    print(f"   ✅ Message sent")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.data_sent = "Hi! I spoke with someone on the phone about booking a room for next Thu-Sun. Could you send me a confirmation of the rates discussed? Thanks, Sarah"
    result.notes = "WhatsApp message sent successfully"
    return result


async def demo_wait_whatsapp(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   📲 Waiting for WhatsApp reply...")
    time.sleep(1)
    print(f"   📲 Reply received after 3.2 hours!")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = 3.2 * 3600
    result.data_received = "Hi Sarah, thanks for reaching out! I can confirm Executive Room at £259/night for Thu-Sun. Shall I book it? You can also book directly at grandhotel.com/book. Best, Sophie"
    result.scores = {"overall": 70}
    result.notes = "Replied in 3.2 hours (acceptable for WhatsApp). Referenced the correct room and rate. Provided booking link. But didn't mention conference rate or any extras."
    return result


async def demo_followup(step: JourneyStep, context: dict) -> StepResult:
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())

    print(f"   ⏳ Monitoring all channels for follow-up (72 hours)...")
    time.sleep(1)
    print(f"   ⏳ Day 1: No follow-up")
    time.sleep(0.5)
    print(f"   ⏳ Day 2: No follow-up")
    time.sleep(0.5)
    print(f"   ⏳ Day 3: No follow-up")
    time.sleep(0.5)
    print(f"   ❌ No proactive follow-up received in 72 hours")

    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.response_time_seconds = 72 * 3600
    result.scores = {"overall": 10}
    result.notes = "Hotel did NOT follow up proactively within 72 hours. This is a major missed opportunity — the guest was clearly interested but didn't book. A simple 'Hi Sarah, just checking if you'd like to proceed?' could have converted this."
    return result


async def demo_analyze(step: JourneyStep, context: dict) -> StepResult:
    """This step runs the real LLM analysis if API key is available."""
    result = StepResult(step_name=step.name, step_type=step.step_type, started_at=datetime.now())
    print(f"   📊 Analyzing full journey...")
    result.status = StepStatus.COMPLETED
    result.completed_at = datetime.now()
    result.notes = "Analysis complete"
    return result


# ─── Main demo runner ───

async def run_demo_journey(
    target_name: str = "The Grand Hotel London",
    use_real_analysis: bool = True,
) -> dict:
    """Run a fully simulated multi-channel mystery shopping journey."""

    # Create orchestrator with demo handlers
    orch = JourneyOrchestrator()
    orch.register_channel(StepType.BROWSE_WEBSITE, demo_browse)
    orch.register_channel(StepType.WEBCHAT, demo_webchat)
    orch.register_channel(StepType.SEND_EMAIL, demo_send_email)
    orch.register_channel(StepType.WAIT_EMAIL, demo_wait_email)
    orch.register_channel(StepType.PHONE_CALL, demo_phone_call)
    orch.register_channel(StepType.SEND_WHATSAPP, demo_whatsapp)
    orch.register_channel(StepType.WAIT_WHATSAPP, demo_wait_whatsapp)
    orch.register_channel(StepType.WAIT_FOLLOWUP, demo_followup)
    orch.register_channel(StepType.ANALYZE, demo_analyze)

    # Create journey plan
    plan = JourneyPlan(
        name=f"Full Mystery Shop - {target_name}",
        description="Complete omnichannel mystery shopping journey",
        persona={
            "name": "Sarah Mitchell",
            "style": "Professional, polite, time-pressed business traveler",
        },
        target={
            "name": target_name,
            "website": "https://www.grandhotel.com",
            "email": "reservations@grandhotel.com",
            "phone": "+44 20 7946 0958",
            "whatsapp": "+44 20 7946 0958",
        },
        steps=[
            JourneyStep("Browse Hotel Website", StepType.BROWSE_WEBSITE,
                        config={"url": "https://www.grandhotel.com"}),
            JourneyStep("Webchat Inquiry", StepType.WEBCHAT,
                        config={"message": "Looking for a quiet room..."}),
            JourneyStep("Email Inquiry", StepType.SEND_EMAIL,
                        config={"to": "reservations@grandhotel.com"}),
            JourneyStep("Wait for Email Reply", StepType.WAIT_EMAIL,
                        config={"timeout_hours": 48}),
            JourneyStep("Phone Call", StepType.PHONE_CALL,
                        config={"phone_number": "+44 20 7946 0958", "reference_previous": True}),
            JourneyStep("WhatsApp Message", StepType.SEND_WHATSAPP,
                        config={"to": "+44 20 7946 0958", "message": "Following up on booking..."}),
            JourneyStep("Wait WhatsApp Reply", StepType.WAIT_WHATSAPP,
                        config={"from": "+44 20 7946 0958", "timeout_hours": 24}),
            JourneyStep("Follow-up Monitoring", StepType.WAIT_FOLLOWUP,
                        config={"timeout_hours": 72}),
            JourneyStep("Full Journey Analysis", StepType.ANALYZE,
                        config={"analyze_all_steps": True}),
        ],
    )

    # Execute
    results = await orch.execute(plan)
    journey_report = orch.get_journey_report()

    # Run LLM analysis if possible
    analysis = None
    if use_real_analysis:
        try:
            from ..config import config as cfg
            if cfg.OPENAI_API_KEY:
                print("\n📊 Running AI analysis of full journey...")
                analysis = analyze_full_journey(journey_report)
                print(f"   Overall Score: {analysis.get('overall_score', 'N/A')}/100")
                print(f"   Benchmark: {analysis.get('competitive_benchmark', 'N/A')}")
                print(f"\n   Executive Summary:")
                print(f"   {analysis.get('executive_summary', '')}")
        except Exception as e:
            print(f"   ⚠️ Analysis error: {e}")

    if not analysis:
        # Fallback static analysis
        analysis = {
            "dimensions": [
                {"name": "First Impression", "score": 78, "notes": "Good website with booking widget and chat"},
                {"name": "Response Speed", "score": 52, "notes": "Email took 6.5 hours, should be under 4"},
                {"name": "Personalization", "score": 55, "notes": "Generic responses, didn't tailor to conference needs"},
                {"name": "Cross-Channel Consistency", "score": 60, "notes": "Phone agent knew about email, but email didn't reference chat"},
                {"name": "Product Knowledge", "score": 62, "notes": "Basic knowledge but unsure about conference rates"},
                {"name": "Proactive Service", "score": 40, "notes": "No upselling, no conference packages offered"},
                {"name": "Follow-up", "score": 10, "notes": "No follow-up in 72 hours — major failure"},
                {"name": "Booking Conversion", "score": 45, "notes": "Never pushed for booking, passive approach"},
                {"name": "Overall Hospitality", "score": 65, "notes": "Polite but not memorable"},
            ],
            "overall_score": 52,
            "executive_summary": "The Grand Hotel provides adequate but uninspired service across channels. The biggest issue is the complete lack of follow-up — a highly interested guest was left without any proactive contact for 72 hours. Email response time (6.5 hours) is too slow for a luxury property. Cross-channel awareness exists but isn't leveraged for personalization.",
            "top_strengths": ["Website has live chat and booking widget", "Phone agent was aware of prior email", "WhatsApp reply included booking link"],
            "critical_improvements": ["Must follow up with interested guests within 24-48 hours", "Email response time must be under 4 hours", "Train staff on conference packages and proactive upselling", "Create cross-channel guest profiles for seamless experience"],
            "revenue_impact": "Estimated 30-40% of email inquiries are lost due to slow response. Zero follow-up means an estimated 50% of 'thinking about it' guests are lost to competitors. For a hotel doing 100 inquiries/month, this could mean 20-30 lost bookings worth £15,000-£25,000/month.",
            "competitive_benchmark": "Below Average",
            "quick_wins": [
                "Set up auto-reply for email inquiries confirming receipt and ETA",
                "Create a 48-hour follow-up task for all unbooked inquiries",
                "Brief all staff on current promotions and conference rates",
                "Add direct booking link to every email reply",
            ],
        }

    # Generate HTML report
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html = generate_journey_html_report(journey_report, analysis, target_name)
    html_path = f"data/journey_{timestamp}.html"
    with open(html_path, "w") as f:
        f.write(html)
    print(f"\n🌐 Full journey report saved: {html_path}")

    # Save JSON
    json_path = html_path.replace(".html", ".json")
    full_data = {"journey": journey_report, "analysis": analysis}
    with open(json_path, "w") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)
    print(f"📄 JSON data saved: {json_path}")

    return full_data


def main():
    asyncio.run(run_demo_journey())


if __name__ == "__main__":
    main()
