"""Hotel mystery shopping scenarios."""

PERSONAS = [
    {
        "name": "Sarah Mitchell",
        "background": "Business traveler, mid-30s, traveling for a conference",
        "style": "Professional, polite but time-pressed",
        "needs": {
            "dates": "next Thursday to Sunday (3 nights)",
            "guests": "1 adult",
            "room_type": "quiet room, preferably high floor",
            "budget": "doesn't mention budget unless asked",
            "purpose": "attending a tech conference nearby",
            "extras": "interested in late checkout, wants to know about gym/wifi",
        },
    },
    {
        "name": "James & Emma Cooper",
        "background": "Couple planning anniversary weekend, late 40s",
        "style": "Warm, enthusiastic, wants to feel special",
        "needs": {
            "dates": "next Saturday to Monday (2 nights)",
            "guests": "2 adults",
            "room_type": "best room available, sea view if possible",
            "budget": "willing to spend more for the right experience",
            "purpose": "wedding anniversary celebration",
            "extras": "interested in restaurant recommendations, spa, champagne in room",
        },
    },
    {
        "name": "David Chen",
        "background": "Family traveler, booking for family of 4 with young kids",
        "style": "Practical, lots of questions, wants value for money",
        "needs": {
            "dates": "school holiday period, flexible on exact dates",
            "guests": "2 adults, 2 children (ages 5 and 8)",
            "room_type": "family room or connecting rooms",
            "budget": "cost-conscious, asks about deals/packages",
            "purpose": "family holiday",
            "extras": "kids activities, pool, breakfast included?, parking",
        },
    },
]

# Scoring criteria for hotel phone calls
PHONE_SCORING_CRITERIA = [
    {
        "id": "answer_speed",
        "name": "Answer Speed",
        "description": "How quickly was the phone answered?",
        "weight": 10,
        "rubric": {
            "90-100": "Answered within 3 rings",
            "70-89": "Answered within 5 rings",
            "50-69": "Answered within 8 rings",
            "30-49": "Answered after long wait",
            "0-29": "Not answered / voicemail",
        },
    },
    {
        "id": "greeting",
        "name": "Professional Greeting",
        "description": "Did staff greet properly with hotel name and offer to help?",
        "weight": 10,
        "rubric": {
            "90-100": "Full greeting: hotel name + staff name + offer to help",
            "70-89": "Hotel name + offer to help",
            "50-69": "Generic greeting without hotel name",
            "0-49": "No proper greeting",
        },
    },
    {
        "id": "needs_discovery",
        "name": "Needs Discovery",
        "description": "Did staff ask about dates, guests, purpose, preferences?",
        "weight": 20,
        "rubric": {
            "90-100": "Asked about dates, guests, purpose, and preferences proactively",
            "70-89": "Asked about dates and guests, some preferences",
            "50-69": "Only asked basic dates",
            "0-49": "Didn't ask or rushed through",
        },
    },
    {
        "id": "product_knowledge",
        "name": "Product Knowledge",
        "description": "Did staff demonstrate knowledge of rooms, amenities, area?",
        "weight": 15,
        "rubric": {
            "90-100": "Detailed knowledge of room types, amenities, and local area",
            "70-89": "Good knowledge of rooms and basic amenities",
            "50-69": "Limited knowledge, had to check on things",
            "0-49": "Poor knowledge, couldn't answer basic questions",
        },
    },
    {
        "id": "upsell",
        "name": "Upselling & Recommendations",
        "description": "Did staff suggest upgrades, packages, or additional services?",
        "weight": 15,
        "rubric": {
            "90-100": "Naturally suggested relevant upgrades and extras",
            "70-89": "Mentioned some upgrades when appropriate",
            "50-69": "Only mentioned extras when directly asked",
            "0-49": "No upselling at all",
        },
    },
    {
        "id": "rate_transparency",
        "name": "Rate & Availability",
        "description": "Were rates clearly communicated with value justification?",
        "weight": 10,
        "rubric": {
            "90-100": "Clear rates with value explanation, mentioned direct booking benefits",
            "70-89": "Clear rates provided",
            "50-69": "Vague about rates, suggested checking website",
            "0-49": "Refused to give rates or redirected entirely",
        },
    },
    {
        "id": "closing",
        "name": "Closing & Follow-up",
        "description": "Did staff attempt to secure booking or arrange follow-up?",
        "weight": 15,
        "rubric": {
            "90-100": "Asked for the booking, offered to hold rate, arranged follow-up",
            "70-89": "Encouraged booking, offered to send info",
            "50-69": "Left it to the caller with no follow-up offered",
            "0-49": "Abrupt ending, no attempt to close",
        },
    },
    {
        "id": "warmth",
        "name": "Warmth & Hospitality",
        "description": "Overall tone, friendliness, and genuine hospitality feel",
        "weight": 5,
        "rubric": {
            "90-100": "Genuinely warm, made caller feel welcome and valued",
            "70-89": "Friendly and professional",
            "50-69": "Polite but transactional",
            "0-49": "Cold, disinterested, or rude",
        },
    },
]

# Scoring criteria for hotel email responses
EMAIL_SCORING_CRITERIA = [
    {
        "id": "response_time",
        "name": "Response Time",
        "description": "How quickly did the hotel respond to the inquiry email?",
        "weight": 20,
        "rubric": {
            "90-100": "Within 1 hour",
            "70-89": "Within 4 hours",
            "50-69": "Within 24 hours",
            "30-49": "Within 48 hours",
            "0-29": "More than 48 hours or no response",
        },
    },
    {
        "id": "personalization",
        "name": "Personalization",
        "description": "Was the reply personalized or a generic template?",
        "weight": 15,
        "rubric": {
            "90-100": "Addressed by name, referenced specific requests, tailored suggestions",
            "70-89": "Addressed by name, some personalization",
            "50-69": "Generic reply with some relevant info",
            "0-49": "Clearly a copy-paste template",
        },
    },
    {
        "id": "completeness",
        "name": "Completeness",
        "description": "Did the reply answer all questions asked in the inquiry?",
        "weight": 20,
        "rubric": {
            "90-100": "All questions answered plus additional helpful info",
            "70-89": "Most questions answered",
            "50-69": "Some questions answered, others ignored",
            "0-49": "Most questions ignored",
        },
    },
    {
        "id": "rate_info",
        "name": "Rate & Availability Info",
        "description": "Were specific rates and availability provided?",
        "weight": 15,
        "rubric": {
            "90-100": "Specific rates for requested dates with room options",
            "70-89": "General rate range provided",
            "50-69": "Directed to website for rates",
            "0-49": "No rate information at all",
        },
    },
    {
        "id": "call_to_action",
        "name": "Call to Action",
        "description": "Did the reply encourage booking or next step?",
        "weight": 15,
        "rubric": {
            "90-100": "Clear CTA with direct booking link/offer, sense of urgency",
            "70-89": "Encouraged booking, provided booking method",
            "50-69": "Passive — 'let us know if interested'",
            "0-49": "No call to action",
        },
    },
    {
        "id": "professionalism",
        "name": "Professionalism & Tone",
        "description": "Was the email well-written, professional, and on-brand?",
        "weight": 10,
        "rubric": {
            "90-100": "Excellent writing, warm tone, proper formatting, hotel branding",
            "70-89": "Professional and clear",
            "50-69": "Acceptable but bland or has minor errors",
            "0-49": "Poor grammar, unprofessional, or sloppy",
        },
    },
    {
        "id": "follow_up",
        "name": "Follow-up",
        "description": "Did the hotel follow up if no reply was sent?",
        "weight": 5,
        "rubric": {
            "90-100": "Sent a follow-up within 2-3 days",
            "50-69": "No follow-up but mentioned they would",
            "0-49": "No follow-up at all",
        },
    },
]


def get_email_scenario(persona_index: int = 0) -> dict:
    """Generate an email inquiry scenario."""
    persona = PERSONAS[persona_index % len(PERSONAS)]
    needs = persona["needs"]

    subject_templates = [
        f"Room availability inquiry - {needs['dates']}",
        f"Booking inquiry for {needs['dates']}",
        f"Question about availability",
    ]

    body_template = f"""Hi there,

I'm looking to book a stay at your hotel. Here are the details:

- Dates: {needs['dates']}
- Guests: {needs['guests']}
- Room preference: {needs['room_type']}
- Purpose: {needs['purpose']}

I'd also like to know about: {needs['extras']}

Could you let me know about availability and rates?

Best regards,
{persona['name']}"""

    return {
        "persona": persona,
        "subject": subject_templates[0],
        "body": body_template,
        "scoring_criteria": EMAIL_SCORING_CRITERIA,
    }


def get_phone_scenario(persona_index: int = 0) -> dict:
    """Generate a phone call scenario."""
    persona = PERSONAS[persona_index % len(PERSONAS)]

    system_prompt = f"""You are {persona['name']}, a potential hotel guest calling to inquire about a stay.

Your background: {persona['background']}
Your communication style: {persona['style']}

What you're looking for:
- Dates: {persona['needs']['dates']}
- Guests: {persona['needs']['guests']}
- Room preference: {persona['needs']['room_type']}
- Purpose: {persona['needs']['purpose']}
- Additional interests: {persona['needs']['extras']}
- Budget: {persona['needs']['budget']}

BEHAVIOR INSTRUCTIONS:
1. Start by saying you're interested in booking a stay
2. Share your dates and basic needs
3. Ask about room types and rates
4. Ask about {persona['needs']['extras']}
5. If they don't ask about your needs, volunteer info naturally
6. Be conversational and natural — you're a real person calling
7. If they try to upsell, be receptive but not immediately committed
8. End the call naturally — either by saying you'll think about it, or asking them to send info via email
9. Keep the call under 3 minutes

IMPORTANT: You are testing their service quality. Note mentally:
- How long before they answered
- Did they greet properly
- Did they ask about your needs
- Did they offer upgrades/extras
- Were they knowledgeable
- Did they try to close/follow up
"""

    return {
        "persona": persona,
        "system_prompt": system_prompt,
        "scoring_criteria": PHONE_SCORING_CRITERIA,
    }
