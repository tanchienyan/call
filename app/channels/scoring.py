"""AI scoring engine — analyzes transcripts, emails, and full journeys."""

import json
from openai import OpenAI
from ..config import settings


def score_phone_call(transcript: str, hotel_name: str = "") -> dict:
    """Score a phone call transcript."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""You are an expert mystery shopping analyst. Score this hotel phone call transcript.

Hotel: {hotel_name}

Transcript:
{transcript}

Score each dimension 0-100:

1. greeting_professionalism - How professional was the initial greeting?
2. response_time - How quickly did they engage? (deduct for long holds/transfers)
3. product_knowledge - Did they know their rooms, rates, amenities?
4. listening_skills - Did they listen to what the caller needed?
5. personalization - Did they tailor the response to the caller?
6. upselling - Did they suggest upgrades, packages, or extras?
7. closing_skills - Did they try to convert the inquiry to a booking?
8. overall_warmth - Did the caller feel welcomed and valued?

Also analyze:
- staff_name: name of the person who helped (if mentioned)
- key_info_provided: what info did they actually give?
- missed_opportunities: what should they have done better?
- red_flags: any concerning behavior?
- best_moments: what did they do well?

Return JSON:
{{
  "scores": {{
    "greeting_professionalism": 0-100,
    "response_time": 0-100,
    "product_knowledge": 0-100,
    "listening_skills": 0-100,
    "personalization": 0-100,
    "upselling": 0-100,
    "closing_skills": 0-100,
    "overall_warmth": 0-100
  }},
  "overall_score": 0-100,
  "staff_name": "...",
  "key_info_provided": ["..."],
  "missed_opportunities": ["..."],
  "red_flags": ["..."],
  "best_moments": ["..."],
  "summary": "2-3 sentence assessment"
}}"""}],
    )
    return json.loads(resp.choices[0].message.content)


def score_email_reply(sent_email: str, reply_email: str, response_time_hours: float = 0, hotel_name: str = "") -> dict:
    """Score an email reply from a hotel."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""Score this hotel's email response to a booking inquiry.

Hotel: {hotel_name}
Response time: {response_time_hours:.1f} hours

Original inquiry:
{sent_email}

Hotel's reply:
{reply_email}

Score each dimension 0-100:

1. response_speed - Based on {response_time_hours:.1f}h response time (< 1h = 95+, 1-4h = 80+, 4-12h = 60+, 12-24h = 40+, >24h = 20-)
2. completeness - Did they answer all questions asked?
3. personalization - Did they use the guest's name, reference their needs?
4. professionalism - Grammar, tone, formatting
5. sales_effectiveness - Did they try to convert the inquiry?
6. upselling - Did they suggest extras, packages, upgrades?
7. warmth - Did it feel personal or like a template?
8. call_to_action - Was there a clear next step?

Return JSON:
{{
  "scores": {{
    "response_speed": 0-100,
    "completeness": 0-100,
    "personalization": 0-100,
    "professionalism": 0-100,
    "sales_effectiveness": 0-100,
    "upselling": 0-100,
    "warmth": 0-100,
    "call_to_action": 0-100
  }},
  "overall_score": 0-100,
  "questions_answered": ["which questions from the inquiry were answered"],
  "questions_missed": ["which were not"],
  "missed_opportunities": ["..."],
  "best_moments": ["..."],
  "summary": "2-3 sentence assessment"
}}"""}],
    )
    return json.loads(resp.choices[0].message.content)


def score_full_journey(steps: list[dict], hotel_name: str = "") -> dict:
    """Score an entire multi-channel mystery shopping journey."""
    steps_text = ""
    for s in steps:
        steps_text += f"\n### {s.get('step_name', '')} ({s.get('step_type', '')})\n"
        steps_text += f"Status: {s.get('status', '')}\n"
        if s.get("response_time_seconds"):
            h = s["response_time_seconds"] / 3600
            steps_text += f"Response time: {h:.1f}h\n" if h >= 1 else f"Response time: {s['response_time_seconds']:.0f}s\n"
        if s.get("data_sent"):
            steps_text += f"Sent: {s['data_sent'][:500]}\n"
        if s.get("data_received") or s.get("transcript"):
            text = s.get("transcript") or s.get("data_received", "")
            steps_text += f"Received: {text[:500]}\n"
        if s.get("notes"):
            steps_text += f"Notes: {s['notes']}\n"
        if s.get("score") is not None:
            steps_text += f"Channel score: {s['score']}/100\n"

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": f"""You are an expert mystery shopping analyst. Analyze this complete
multi-channel customer journey for {hotel_name}.

{steps_text}

Score these dimensions 0-100:
1. First Impression - Website quality, professionalism
2. Response Speed - Speed across all channels
3. Personalization - Tailored responses to customer needs
4. Cross-Channel Consistency - Did info match across channels?
5. Product Knowledge - Staff knowledge of rooms, rates, amenities
6. Proactive Service - Upselling, suggestions, anticipating needs
7. Follow-up - Proactive chase after inquiry
8. Booking Conversion - Effectiveness at converting to booking
9. Overall Hospitality - Feeling of being welcomed

Return JSON:
{{
  "dimensions": [
    {{"name": "First Impression", "score": 0-100, "notes": "..."}},
    ...all 9 dimensions...
  ],
  "overall_score": 0-100,
  "letter_grade": "A/B/C/D/F",
  "executive_summary": "2-3 sentences for the hotel GM",
  "top_strengths": ["..."],
  "critical_improvements": ["..."],
  "revenue_impact": "How issues affect revenue",
  "competitive_benchmark": "poor/below average/average/above average/excellent",
  "quick_wins": ["Things fixable immediately"],
  "channel_ranking": [
    {{"channel": "phone/email/webchat/etc", "score": 0-100, "verdict": "..."}}
  ]
}}"""}],
    )
    return json.loads(resp.choices[0].message.content)
