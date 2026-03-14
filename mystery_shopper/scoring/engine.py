"""LLM-based scoring engine for mystery shopping interactions."""

import json
from openai import OpenAI
from ..config import config
from ..models import ScoreItem


def score_interaction(
    channel: str,
    criteria: list[dict],
    outbound_content: str,
    inbound_content: str,
    response_time_seconds: float | None = None,
    context: str = "",
) -> dict:
    """Score an interaction using LLM analysis.

    Returns dict with:
        - scores: list of ScoreItem
        - overall_score: int
        - summary: str
        - strengths: list[str]
        - improvements: list[str]
    """
    criteria_text = ""
    for c in criteria:
        criteria_text += f"\n### {c['name']} (weight: {c['weight']}%)\n"
        criteria_text += f"{c['description']}\n"
        criteria_text += "Scoring rubric:\n"
        for range_str, desc in c["rubric"].items():
            criteria_text += f"  - {range_str}: {desc}\n"

    prompt = f"""You are an expert mystery shopping analyst evaluating a {channel} interaction with a hotel.

## Context
{context}

## What was sent (mystery shopper's inquiry):
{outbound_content}

## What was received (hotel's response):
{inbound_content}

{"## Response Time: " + str(round(response_time_seconds / 3600, 1)) + " hours" if response_time_seconds else ""}

## Scoring Criteria
{criteria_text}

## Instructions
Score each criterion on a scale of 0-100 based on the rubric provided. Be fair but thorough.
Consider the response time data if available.

Return your analysis as JSON in this exact format:
{{
    "scores": [
        {{"criterion_id": "...", "criterion_name": "...", "score": 0-100, "notes": "brief explanation"}},
        ...
    ],
    "summary": "2-3 sentence overall assessment",
    "strengths": ["strength 1", "strength 2", ...],
    "improvements": ["improvement 1", "improvement 2", ...]
}}

Return ONLY valid JSON, no markdown formatting."""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    # Convert to ScoreItems
    score_items = []
    for s in result.get("scores", []):
        score_items.append(
            ScoreItem(
                criterion=s.get("criterion_name", s.get("criterion_id", "")),
                score=s.get("score", 0),
                notes=s.get("notes", ""),
            )
        )

    # Calculate weighted overall score
    total_weight = sum(c["weight"] for c in criteria)
    weighted_sum = 0
    for s in result.get("scores", []):
        crit_id = s.get("criterion_id", "")
        matching = [c for c in criteria if c["id"] == crit_id]
        weight = matching[0]["weight"] if matching else 1
        weighted_sum += s.get("score", 0) * weight
    overall_score = int(weighted_sum / total_weight) if total_weight > 0 else 0

    return {
        "scores": score_items,
        "overall_score": overall_score,
        "summary": result.get("summary", ""),
        "strengths": result.get("strengths", []),
        "improvements": result.get("improvements", []),
    }
