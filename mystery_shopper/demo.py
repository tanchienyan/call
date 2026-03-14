"""Demo mode — simulates a full mystery shopping session without real API calls."""

import random
import time
from datetime import datetime, timedelta

from .models import (
    Channel, ChannelResult, MysteryShopSession, ScoreItem, Target, TestStatus,
)
from .scenarios.hotel import EMAIL_SCORING_CRITERIA, PHONE_SCORING_CRITERIA
from .reporting.report import generate_text_report, generate_html_report


# Simulated hotel responses for demo
SIMULATED_EMAIL_REPLIES = {
    "good": {
        "response_hours": 1.5,
        "reply": """Dear Sarah,

Thank you for your inquiry! We'd love to welcome you for your conference stay.

For next Thursday to Sunday (3 nights), I'm delighted to confirm we have availability:

- **Superior Room (high floor)**: £189/night — quiet location, city view
- **Executive Room (high floor)**: £249/night — larger room, lounge access, complimentary breakfast
- **Junior Suite (top floor)**: £329/night — separate sitting area, premium amenities

All rooms include complimentary high-speed WiFi and access to our 24-hour fitness center.

For conference guests, we're currently offering a 10% discount on direct bookings — just mention code CONF2026 when booking.

Regarding late checkout, we can usually arrange this until 2pm subject to availability. I'd recommend our Executive Room for conference stays — the lounge access gives you a quiet workspace and the breakfast saves time in the morning.

Shall I hold a room for you? I'm happy to process the booking directly or answer any other questions.

Warm regards,
Maria Garcia
Reservations Team
The Grand Hotel""",
    },
    "average": {
        "response_hours": 8.0,
        "reply": """Hi,

Thanks for your email. We have rooms available for those dates.

Our rates start from £189 per night. You can check availability and book on our website at www.grandhotel.com.

WiFi is included and we have a gym.

Let us know if you need anything else.

Regards,
Reservations""",
    },
    "poor": {
        "response_hours": 36.0,
        "reply": """Hi Sarah,

Please visit our website to check rates and availability.

www.grandhotel.com

Thanks""",
    },
}

SIMULATED_PHONE_TRANSCRIPTS = {
    "good": {
        "duration_seconds": 180,
        "transcript": """[Ring 1] [Ring 2]
Hotel: Good afternoon, The Grand Hotel, this is Maria speaking. How may I help you today?
Caller: Hi, I'm calling to inquire about booking a room at your hotel.
Hotel: Of course! I'd be happy to help. Are you looking at specific dates?
Caller: Yes, I'd like to stay from next Thursday to Sunday, so three nights.
Hotel: Wonderful — Thursday to Sunday, three nights. And is that for yourself, or will there be other guests?
Caller: Just myself, I'm attending a tech conference nearby.
Hotel: Oh lovely! We actually host quite a few conference guests. May I ask — do you have a preference for room type? We have several options that might work well for a business stay.
Caller: I'd prefer a quiet room, high floor if possible.
Hotel: Absolutely. I'd actually recommend our Executive Room on the 8th floor — it's away from the street side, very quiet, and it comes with access to our Executive Lounge where you can work between sessions. It includes complimentary breakfast as well, which is a time-saver during conferences.
Caller: That sounds nice. What's the rate?
Hotel: The Executive Room is £249 per night. We also have our Superior Room at £189 if you'd prefer something more straightforward. Both include WiFi and gym access. For conference guests, we're offering 10% off direct bookings — that would bring the Executive down to about £224.
Caller: Okay, and what about late checkout?
Hotel: We can usually accommodate late checkout until 2pm, especially midweek. I can make a note on the reservation to arrange that. Is there anything else I can help with — perhaps restaurant recommendations near the conference venue?
Caller: That's very helpful, thank you. Let me think about it and I'll get back to you.
Hotel: Of course! Would you like me to email you a summary with the rates and a direct booking link? That way you'll have everything to hand.
Caller: Yes, that would be great. My email is sarah@email.com.
Hotel: Perfect, I'll send that over right away. Thank you for calling, Sarah — we'd love to welcome you next week!
Caller: Thanks, goodbye.
Hotel: Goodbye, have a lovely day!""",
    },
    "average": {
        "duration_seconds": 90,
        "transcript": """[Ring 1] [Ring 2] [Ring 3] [Ring 4] [Ring 5]
Hotel: Grand Hotel, hello?
Caller: Hi, I'm calling to inquire about booking a room at your hotel.
Hotel: Sure, what dates?
Caller: Next Thursday to Sunday, three nights.
Hotel: Okay, let me check... yes we have rooms. Standard room is £189.
Caller: Do you have anything on a high floor? I'd like a quiet room.
Hotel: Uh, I think we might have something higher up. I'd have to check.
Caller: I'm attending a conference nearby. Do you have any deals for that?
Hotel: I'm not sure about conference deals, you might want to check our website.
Caller: Okay. What about late checkout?
Hotel: You'd have to ask at reception when you check in.
Caller: Alright, I'll think about it. Thank you.
Hotel: Okay, thanks for calling. Bye.""",
    },
    "poor": {
        "duration_seconds": 45,
        "transcript": """[Ring 1] [Ring 2] [Ring 3] [Ring 4] [Ring 5] [Ring 6] [Ring 7] [Ring 8]
Hotel: Hello?
Caller: Hi, I'm calling to inquire about booking a room at your hotel.
Hotel: What dates?
Caller: Next Thursday to Sunday.
Hotel: Hold on... yeah we have rooms. Check the website for prices.
Caller: Could you tell me the rates?
Hotel: It depends on the room type. It's all on the website. www.grandhotel.com.
Caller: I'd prefer a quiet room on a high floor—
Hotel: Yeah, just mention that when you book online. Anything else?
Caller: No, I guess that's it. Thank you.
Hotel: Okay, bye.""",
    },
}


def _simulate_scores(criteria: list[dict], quality: str) -> list[ScoreItem]:
    """Generate simulated scores based on quality level."""
    ranges = {
        "good": (75, 98),
        "average": (45, 75),
        "poor": (10, 45),
    }
    lo, hi = ranges.get(quality, (40, 70))

    scores = []
    for c in criteria:
        score = random.randint(lo, hi)
        notes = ""
        # Find matching rubric
        for range_str, desc in c["rubric"].items():
            parts = range_str.split("-")
            if len(parts) == 2:
                r_lo, r_hi = int(parts[0]), int(parts[1])
                if r_lo <= score <= r_hi:
                    notes = desc
                    break
        scores.append(ScoreItem(criterion=c["name"], score=score, notes=notes))

    return scores


def run_demo(
    target_name: str = "The Grand Hotel",
    quality: str = "average",
    channels: list[str] | None = None,
    output_html: str | None = None,
) -> MysteryShopSession:
    """Run a simulated mystery shopping demo.

    Args:
        target_name: Name of the hotel
        quality: "good", "average", or "poor" — simulated response quality
        channels: List of channels to test ("email", "phone"). Default: both
        output_html: Path to save HTML report
    """
    if channels is None:
        channels = ["email", "phone"]

    target = Target(
        name=target_name,
        industry="hotel",
        email="reservations@grandhotel.com",
        phone="+44 20 1234 5678",
    )

    session = MysteryShopSession(
        target=target,
        scenario_name=f"Hotel Inquiry (Demo — {quality} quality)",
    )

    print(f"\n🕵️  AI Mystery Shopper — Demo Mode")
    print(f"   Target: {target_name}")
    print(f"   Simulated quality: {quality}")
    print()

    if "email" in channels:
        print("📧 Simulating email inquiry...")
        time.sleep(1)

        email_data = SIMULATED_EMAIL_REPLIES.get(quality, SIMULATED_EMAIL_REPLIES["average"])
        email_result = ChannelResult(
            channel=Channel.EMAIL,
            status=TestStatus.COMPLETED,
            started_at=datetime.now() - timedelta(hours=email_data["response_hours"]),
            completed_at=datetime.now(),
            outbound_content=(
                "Subject: Room availability inquiry - next Thursday to Sunday\n\n"
                "Hi there,\n\nI'm looking to book a stay at your hotel...\n"
                "- Dates: next Thursday to Sunday (3 nights)\n"
                "- Guests: 1 adult\n"
                "- Room preference: quiet room, high floor\n"
                "- Purpose: attending a tech conference\n\n"
                "Could you let me know about availability and rates?\n\n"
                "Best regards,\nSarah Mitchell"
            ),
            inbound_content=email_data["reply"],
            response_time_seconds=email_data["response_hours"] * 3600,
        )

        scores = _simulate_scores(EMAIL_SCORING_CRITERIA, quality)
        email_result.scores = scores
        total_weight = sum(c["weight"] for c in EMAIL_SCORING_CRITERIA)
        email_result.overall_score = int(
            sum(s.score * c["weight"] for s, c in zip(scores, EMAIL_SCORING_CRITERIA)) / total_weight
        )

        # Generate summary based on quality
        summaries = {
            "good": "Excellent email response — fast, personalized, and proactive. Staff provided detailed options, relevant upselling, and a clear call to action.",
            "average": "Adequate response but lacking personalization and proactiveness. Rates were mentioned but without options or value justification. No follow-up offered.",
            "poor": "Very poor email response — slow, minimal content, and essentially redirected to the website. No effort to engage or convert the inquiry.",
        }
        email_result.summary = summaries.get(quality, summaries["average"])

        strengths_map = {
            "good": ["Fast response time", "Personalized reply addressing specific needs", "Proactive upselling with relevant recommendations", "Clear call to action with booking offer"],
            "average": ["Did respond to the inquiry", "Basic rate information provided"],
            "poor": [],
        }
        email_result.strengths = strengths_map.get(quality, [])

        improvements_map = {
            "good": ["Could include a link to virtual room tour"],
            "average": ["Respond faster — 8 hours is too slow for a booking inquiry", "Personalize the response to the guest's stated needs", "Provide specific room options with rates", "Include a direct booking CTA"],
            "poor": ["Must respond within 4 hours maximum", "Provide actual rates and availability — don't redirect to website", "Address the guest by name and reference their specific inquiry", "Include upselling opportunities", "Offer a clear next step to book"],
        }
        email_result.improvements = improvements_map.get(quality, [])

        session.results["email"] = email_result
        print(f"   ✅ Email score: {email_result.overall_score}/100")

    if "phone" in channels:
        print("\n📞 Simulating phone call...")
        time.sleep(1)

        phone_data = SIMULATED_PHONE_TRANSCRIPTS.get(quality, SIMULATED_PHONE_TRANSCRIPTS["average"])
        phone_result = ChannelResult(
            channel=Channel.PHONE,
            status=TestStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=phone_data["duration_seconds"]),
            completed_at=datetime.now(),
            outbound_content="AI called +44 20 1234 5678 as Sarah Mitchell (business traveler, conference attendee)",
            inbound_content=phone_data["transcript"],
            response_time_seconds=phone_data["duration_seconds"],
        )

        scores = _simulate_scores(PHONE_SCORING_CRITERIA, quality)
        phone_result.scores = scores
        total_weight = sum(c["weight"] for c in PHONE_SCORING_CRITERIA)
        phone_result.overall_score = int(
            sum(s.score * c["weight"] for s, c in zip(scores, PHONE_SCORING_CRITERIA)) / total_weight
        )

        summaries = {
            "good": "Outstanding phone experience. Staff was warm, knowledgeable, and proactive. Excellent needs discovery, relevant upselling, and strong closing with follow-up offer.",
            "average": "Functional but uninspired call. Basic information provided but staff didn't proactively explore needs or offer upgrades. No follow-up arranged.",
            "poor": "Poor phone experience. Staff was disengaged, didn't explore needs, and redirected to website. No attempt at hospitality or relationship building.",
        }
        phone_result.summary = summaries.get(quality, summaries["average"])

        strengths_map = {
            "good": ["Answered quickly with full professional greeting", "Excellent needs discovery — asked about purpose and preferences", "Relevant upselling with value justification", "Strong close — offered to email summary and hold room"],
            "average": ["Did answer the phone", "Provided basic rate"],
            "poor": [],
        }
        phone_result.strengths = strengths_map.get(quality, [])

        improvements_map = {
            "good": ["Could have mentioned loyalty program"],
            "average": ["Answer within 3 rings", "Use a proper greeting with hotel name and staff name", "Ask about the purpose of stay to tailor recommendations", "Know about current promotions and conference deals", "Offer to send information and follow up"],
            "poor": ["Must use a professional greeting", "Never redirect to website on a phone call — the caller chose to call for a reason", "Ask about needs, preferences, and purpose", "Know room types and rates without hesitation", "Show genuine interest and hospitality", "Always offer a follow-up"],
        }
        phone_result.improvements = improvements_map.get(quality, [])

        session.results["phone"] = phone_result
        print(f"   ✅ Phone score: {phone_result.overall_score}/100")

    # Generate reports
    print(f"\n📊 Overall Score: {session.overall_score}/100")
    print()

    text_report = generate_text_report(session)
    print(text_report)

    # Save HTML report
    html_path = output_html or f"data/report_{session.id}.html"
    import os
    os.makedirs(os.path.dirname(html_path) or "data", exist_ok=True)
    html_report = generate_html_report(session)
    with open(html_path, "w") as f:
        f.write(html_report)
    print(f"\n🌐 HTML report saved to: {html_path}")

    # Save JSON
    json_path = html_path.replace(".html", ".json")
    session.save(json_path)
    print(f"📄 JSON data saved to: {json_path}")

    return session
