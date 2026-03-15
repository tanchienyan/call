"""Sentiment & emotion analysis for mystery shopping interactions.

Analyzes text (email replies, chat transcripts, call transcripts) for:
- Sentiment (positive/neutral/negative)
- Emotion detection (warmth, enthusiasm, frustration, indifference...)
- Hospitality-specific tone markers
- Professionalism scoring
- Urgency/sales intent detection
"""

import json
from openai import OpenAI
from ..config import config


def analyze_sentiment(
    text: str,
    channel: str = "email",
    context: str = "",
) -> dict:
    """Run full sentiment and emotion analysis on a piece of text.

    Returns:
        {
            "sentiment": "positive" | "neutral" | "negative",
            "sentiment_score": -1.0 to 1.0,
            "emotions": {
                "warmth": 0-100,
                "enthusiasm": 0-100,
                "professionalism": 0-100,
                "empathy": 0-100,
                "urgency": 0-100,
                "indifference": 0-100,
                "frustration": 0-100,
            },
            "hospitality_markers": {
                "used_guest_name": bool,
                "personalized_response": bool,
                "showed_genuine_interest": bool,
                "offered_help_proactively": bool,
                "created_sense_of_welcome": bool,
                "used_positive_language": bool,
                "mirrored_guest_needs": bool,
            },
            "sales_signals": {
                "attempted_upsell": bool,
                "created_urgency": bool,
                "provided_value_proposition": bool,
                "included_call_to_action": bool,
                "offered_alternatives": bool,
            },
            "tone_description": str,
            "red_flags": [str],
            "positive_highlights": [str],
        }
    """
    prompt = f"""Analyze this {channel} interaction from a hotel staff member for sentiment, emotion, and hospitality quality.

## Context
{context}

## Text to analyze
{text}

## Analysis Required

Return JSON with:
{{
    "sentiment": "positive" or "neutral" or "negative",
    "sentiment_score": float from -1.0 (very negative) to 1.0 (very positive),
    "emotions": {{
        "warmth": 0-100,
        "enthusiasm": 0-100,
        "professionalism": 0-100,
        "empathy": 0-100,
        "urgency": 0-100,
        "indifference": 0-100,
        "frustration": 0-100
    }},
    "hospitality_markers": {{
        "used_guest_name": true/false,
        "personalized_response": true/false,
        "showed_genuine_interest": true/false,
        "offered_help_proactively": true/false,
        "created_sense_of_welcome": true/false,
        "used_positive_language": true/false,
        "mirrored_guest_needs": true/false
    }},
    "sales_signals": {{
        "attempted_upsell": true/false,
        "created_urgency": true/false,
        "provided_value_proposition": true/false,
        "included_call_to_action": true/false,
        "offered_alternatives": true/false
    }},
    "tone_description": "One sentence describing the overall tone",
    "red_flags": ["list of concerning elements, if any"],
    "positive_highlights": ["list of things done well"]
}}

Be specific and honest. Return ONLY valid JSON."""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def analyze_call_transcript(transcript: str) -> dict:
    """Specialized analysis for phone call transcripts.

    In addition to standard sentiment, also analyzes:
    - Turn-by-turn sentiment flow
    - Active listening indicators
    - Interruption patterns
    - Question quality
    - Rapport building
    """
    prompt = f"""Analyze this phone call transcript between a mystery shopper (caller) and hotel staff.

## Transcript
{transcript}

Return JSON with:
{{
    "overall_sentiment": "positive" or "neutral" or "negative",
    "sentiment_score": -1.0 to 1.0,
    "sentiment_flow": [
        {{"turn": 1, "speaker": "hotel", "sentiment": "positive", "note": "warm greeting"}},
        ...
    ],
    "staff_emotions": {{
        "warmth": 0-100,
        "enthusiasm": 0-100,
        "professionalism": 0-100,
        "patience": 0-100,
        "confidence": 0-100,
        "indifference": 0-100
    }},
    "conversation_quality": {{
        "active_listening": 0-100,
        "question_quality": 0-100,
        "rapport_building": 0-100,
        "solution_orientation": 0-100,
        "closing_strength": 0-100
    }},
    "hospitality_markers": {{
        "used_guest_name": true/false,
        "asked_about_purpose": true/false,
        "offered_recommendations": true/false,
        "showed_local_knowledge": true/false,
        "created_personal_connection": true/false,
        "used_positive_framing": true/false
    }},
    "red_flags": ["list of issues"],
    "best_moments": ["moments where staff excelled"],
    "missed_opportunities": ["things staff could have done better"],
    "tone_summary": "One paragraph summary of the call's tone and feel"
}}

Return ONLY valid JSON."""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def compare_channel_sentiment(channel_analyses: dict[str, dict]) -> dict:
    """Compare sentiment across channels to detect consistency.

    Args:
        channel_analyses: {"email": analysis_dict, "phone": analysis_dict, ...}

    Returns:
        Cross-channel sentiment comparison and consistency score.
    """
    prompt_parts = []
    for channel, analysis in channel_analyses.items():
        prompt_parts.append(f"""
### {channel.upper()} Channel
Sentiment: {analysis.get('sentiment', 'N/A')} ({analysis.get('sentiment_score', 'N/A')})
Tone: {analysis.get('tone_description', analysis.get('tone_summary', 'N/A'))}
Warmth: {analysis.get('emotions', analysis.get('staff_emotions', {})).get('warmth', 'N/A')}
Professionalism: {analysis.get('emotions', analysis.get('staff_emotions', {})).get('professionalism', 'N/A')}
""")

    prompt = f"""Compare the sentiment and tone across these customer service channels for the same hotel:

{''.join(prompt_parts)}

Return JSON:
{{
    "consistency_score": 0-100,
    "tone_alignment": "consistent" or "inconsistent" or "mixed",
    "best_channel": "which channel had the best sentiment",
    "worst_channel": "which channel had the worst sentiment",
    "gaps": ["specific inconsistencies between channels"],
    "recommendation": "one sentence recommendation"
}}

Return ONLY valid JSON."""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
