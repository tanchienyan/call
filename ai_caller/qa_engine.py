"""Auto-QA scorecard engine.

Takes a completed call transcript and produces a structured QA scorecard:

- Script adherence: did the agent hit required beats (identity, recording
  consent, pitch, close)? 0-100%.
- Compliance findings: reuses the LiveComplianceTracker's final audit output
  (runs all LLM rules even if they weren't checked live).
- Sentiment curve: per-turn customer sentiment -1 to +1.
- Outcome classification: converted / qualified / declined / voicemail / wrong_number.
- Recommended coaching: free-text suggestions grounded in the transcript.
- Overall score: weighted composite (0-100).

Design note: this engine runs in ~8-15s per call (dominated by LLM calls). For
the demo, Scenario C lands within the <30s target. For the fleet view we
pre-compute scorecards in batches via synth_data.py so 100+ calls render
instantly.

Same design extends to Bloom PDPA healthcare QA — swap rule pack, swap
script-adherence beats, reuse everything else.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, asdict
from typing import Any

from llm import stream_chat
from compliance import CompliancePack, LiveComplianceTracker
import storage


# ─── Data classes ───

@dataclass
class SentimentPoint:
    turn_idx: int
    role: str
    sentiment: float  # -1 to +1
    note: str = ""


@dataclass
class ScorecardSection:
    score: float  # 0-100
    details: dict


@dataclass
class Scorecard:
    call_id: str
    agent_scenario: str
    outcome: str  # converted / qualified / declined / voicemail / wrong_number / other
    overall_score: float  # 0-100
    script_adherence: ScorecardSection
    compliance: ScorecardSection
    sentiment: ScorecardSection
    coaching_recommendations: list[str]
    duration_seconds: float
    word_count: int
    generated_at: float
    generation_ms: float

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ─── Prompts ───

OUTCOME_PROMPT = """You are auditing a call transcript. Classify the call outcome as ONE of:

- converted: customer explicitly agreed to purchase / application / transfer
- qualified: customer expressed interest and was transferred to a human closer
- declined: customer said no / not interested / opted out
- voicemail: reached voicemail, no human pickup
- wrong_number: wrong person / number
- callback: customer requested a callback
- other: anything else

Return ONLY JSON: {"outcome": "...", "confidence": 0.0-1.0, "reason": "one sentence"}"""


SCRIPT_ADHERENCE_PROMPT = """You are evaluating agent script adherence for a Malaysian financial-product outbound call.

Score each beat 0 (missed), 0.5 (partial), or 1 (complete):

1. opening_identity — agent stated their name and company in first 2 turns
2. recording_consent — agent disclosed recording and got explicit consent before discussing product
3. pitch_delivered — agent delivered the core product offer clearly
4. objection_handled — if objection raised, agent addressed it without pressure
5. transfer_or_close — agent initiated warm-transfer OR accepted a clear no
6. compliance_closing — agent thanked customer, did not high-pressure, no urgency tactics

Return ONLY JSON:
{
  "beats": {
    "opening_identity": {"score": 0|0.5|1, "evidence": "quote"},
    "recording_consent": {"score": 0|0.5|1, "evidence": "quote"},
    "pitch_delivered": {"score": 0|0.5|1, "evidence": "quote"},
    "objection_handled": {"score": 0|0.5|1, "evidence": "quote or N/A"},
    "transfer_or_close": {"score": 0|0.5|1, "evidence": "quote"},
    "compliance_closing": {"score": 0|0.5|1, "evidence": "quote"}
  }
}"""


SENTIMENT_PROMPT = """For each USER (customer) turn in the transcript, rate sentiment from -1 (very negative, angry, hostile) to +1 (very positive, enthusiastic). 0 = neutral.

Return ONLY a JSON array of objects: [{"turn_idx": 0, "sentiment": 0.2, "note": "curious"}, ...]

Only include USER turns, not AGENT turns."""


COACHING_PROMPT = """Based on this call transcript, give 3-5 specific coaching points for the human agent. Each should be:
- Actionable (something they can do differently next time)
- Grounded in a specific moment in this call
- Non-generic (no "be more confident")

Return ONLY a JSON array of strings: ["...", "...", "..."]"""


# ─── Engine ───

class QAEngine:
    """Generates scorecards for completed calls."""

    async def score_call(
        self, call_id: str, compliance_pack_id: str | None = None
    ) -> Scorecard:
        """Generate a full QA scorecard for a completed call.

        Latency target: <30s per call (enforced by parallelizing LLM calls).
        """
        t0 = time.monotonic()

        call = storage.get_call(call_id)
        if not call:
            raise ValueError(f"Call not found: {call_id}")

        transcript = call.get("transcript") or []
        if not transcript:
            raise ValueError(f"Empty transcript for call {call_id}")

        transcript_text = self._format_transcript(transcript)
        word_count = sum(len(t.get("text", "").split()) for t in transcript)

        # Run all LLM assessments in parallel
        outcome_task = self._llm_json(OUTCOME_PROMPT, transcript_text)
        adherence_task = self._llm_json(SCRIPT_ADHERENCE_PROMPT, transcript_text)
        sentiment_task = self._llm_json(SENTIMENT_PROMPT, transcript_text)
        coaching_task = self._llm_json(COACHING_PROMPT, transcript_text)

        # Compliance audit via existing tracker
        compliance_task = asyncio.create_task(
            self._run_compliance(transcript, compliance_pack_id)
        )

        outcome, adherence, sentiment, coaching, compliance_flags = await asyncio.gather(
            outcome_task, adherence_task, sentiment_task, coaching_task, compliance_task,
            return_exceptions=True,
        )

        # Resilient to partial failures — substitute empty defaults
        outcome = outcome if isinstance(outcome, dict) else {"outcome": "other", "confidence": 0.0}
        adherence = adherence if isinstance(adherence, dict) else {"beats": {}}
        sentiment = sentiment if isinstance(sentiment, list) else []
        coaching = coaching if isinstance(coaching, list) else []
        compliance_flags = compliance_flags if isinstance(compliance_flags, list) else []

        # Compute section scores
        script_section = self._score_script_adherence(adherence)
        compliance_section = self._score_compliance(compliance_flags)
        sentiment_section = self._score_sentiment(sentiment)

        # Overall: weighted average
        overall = (
            0.35 * script_section.score
            + 0.35 * compliance_section.score
            + 0.30 * sentiment_section.score
        )

        scorecard = Scorecard(
            call_id=call_id,
            agent_scenario=call.get("agent_scenario", "unknown"),
            outcome=outcome.get("outcome", "other"),
            overall_score=round(overall, 1),
            script_adherence=script_section,
            compliance=compliance_section,
            sentiment=sentiment_section,
            coaching_recommendations=coaching[:5],
            duration_seconds=call.get("duration_seconds", 0),
            word_count=word_count,
            generated_at=time.time(),
            generation_ms=round((time.monotonic() - t0) * 1000, 0),
        )

        # Persist scorecard onto the call record
        storage.update_call(call_id, summary=json.dumps(scorecard.to_dict(), ensure_ascii=False))

        return scorecard

    async def _run_compliance(
        self, transcript: list[dict], compliance_pack_id: str | None
    ) -> list[dict]:
        if not compliance_pack_id:
            return []
        try:
            pack = CompliancePack.load(compliance_pack_id)
        except FileNotFoundError:
            return []

        tracker = LiveComplianceTracker(pack)
        for turn in transcript:
            role = turn.get("role", "agent")
            text = turn.get("text", "")
            if text:
                tracker.on_turn(role, text)

        flags = await tracker.final_audit()
        return [f.to_dict() for f in flags]

    @staticmethod
    def _format_transcript(transcript: list[dict]) -> str:
        lines = []
        for i, turn in enumerate(transcript):
            role = turn.get("role", "?").upper()
            text = turn.get("text", "")
            lines.append(f"[{i}] {role}: {text}")
        return "\n".join(lines)

    async def _llm_json(self, prompt: str, transcript_text: str) -> Any:
        """Call LLM and parse JSON response. Returns {} or [] on failure."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict QA auditor for Malaysian telemarketing calls. "
                    "Return ONLY valid JSON as specified — no prose, no markdown."
                ),
            },
            {
                "role": "user",
                "content": f"TRANSCRIPT:\n{transcript_text}\n\n{prompt}",
            },
        ]

        collected = ""
        async def collect(chunk):
            nonlocal collected
            collected += chunk

        try:
            await stream_chat(messages, collect)
        except Exception as e:
            print(f"[QA] LLM error: {e}")
            return {}

        cleaned = collected.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"[QA] Bad JSON response: {collected[:200]}")
            return {} if "{" in collected else []

    # ─── Scoring ───

    def _score_script_adherence(self, adherence: dict) -> ScorecardSection:
        beats = adherence.get("beats", {})
        if not beats:
            return ScorecardSection(score=0.0, details={"beats": {}, "note": "unavailable"})
        total = len(beats)
        achieved = sum(b.get("score", 0) for b in beats.values())
        score = (achieved / total) * 100 if total else 0.0
        return ScorecardSection(score=round(score, 1), details={"beats": beats})

    def _score_compliance(self, flags: list[dict]) -> ScorecardSection:
        if not flags:
            return ScorecardSection(score=100.0, details={"flags": [], "note": "no pack configured"})

        total = len(flags)
        # Each fired flag penalizes by severity
        penalty = 0
        weight_by_severity = {"critical": 35, "high": 20, "medium": 10, "low": 5}
        for f in flags:
            if f.get("status") == "fired":
                penalty += weight_by_severity.get(f.get("severity", "medium"), 10)

        score = max(0, 100 - penalty)
        fired_count = sum(1 for f in flags if f.get("status") == "fired")
        satisfied_count = sum(1 for f in flags if f.get("status") == "satisfied")

        return ScorecardSection(
            score=round(score, 1),
            details={
                "flags": flags,
                "total": total,
                "satisfied": satisfied_count,
                "fired": fired_count,
            },
        )

    def _score_sentiment(self, points: list[dict]) -> ScorecardSection:
        if not points:
            return ScorecardSection(score=50.0, details={"points": [], "curve": []})

        vals = [p.get("sentiment", 0) for p in points if isinstance(p, dict)]
        if not vals:
            return ScorecardSection(score=50.0, details={"points": [], "curve": []})

        avg = sum(vals) / len(vals)
        final = vals[-1] if vals else 0
        # Weighted: 60% average, 40% final turn (how did it END?)
        composite = 0.6 * avg + 0.4 * final
        # Map -1..+1 to 0..100
        score = (composite + 1) / 2 * 100

        return ScorecardSection(
            score=round(score, 1),
            details={
                "points": points,
                "avg": round(avg, 2),
                "final": round(final, 2),
                "curve": vals,
            },
        )


# Singleton for reuse
_engine: QAEngine | None = None


def get_engine() -> QAEngine:
    global _engine
    if _engine is None:
        _engine = QAEngine()
    return _engine


# ─── Fleet aggregation ───

def fleet_summary(scorecards: list[dict]) -> dict:
    """Aggregate scorecards across a fleet of calls.

    Produces: average overall score, outcome distribution, top compliance risks,
    agent ranking (synthetic_agent field on each scorecard), top missed
    objections. Used by the fleet dashboard.
    """
    if not scorecards:
        return {"count": 0}

    count = len(scorecards)
    avg_overall = sum(s.get("overall_score", 0) for s in scorecards) / count
    avg_script = sum(s.get("script_adherence", {}).get("score", 0) for s in scorecards) / count
    avg_compliance = sum(s.get("compliance", {}).get("score", 0) for s in scorecards) / count
    avg_sentiment = sum(s.get("sentiment", {}).get("score", 0) for s in scorecards) / count

    # Outcome distribution
    outcomes: dict[str, int] = {}
    for s in scorecards:
        k = s.get("outcome", "other")
        outcomes[k] = outcomes.get(k, 0) + 1

    # Top compliance violations
    compliance_counts: dict[str, int] = {}
    for s in scorecards:
        flags = s.get("compliance", {}).get("details", {}).get("flags", [])
        for f in flags:
            if f.get("status") == "fired":
                rid = f.get("rule_id", "unknown")
                compliance_counts[rid] = compliance_counts.get(rid, 0) + 1
    top_violations = sorted(compliance_counts.items(), key=lambda x: -x[1])[:5]

    # Agent ranking (if synthetic_agent field present)
    by_agent: dict[str, list[float]] = {}
    for s in scorecards:
        agent = s.get("synthetic_agent") or s.get("agent_scenario", "unknown")
        by_agent.setdefault(agent, []).append(s.get("overall_score", 0))
    agent_ranking = [
        {
            "agent": a,
            "calls": len(scores),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }
        for a, scores in by_agent.items()
    ]
    agent_ranking.sort(key=lambda x: -x["avg_score"])

    # Cross-sell opportunities missed (counted from coaching recommendations)
    missed_opps = 0
    for s in scorecards:
        recs = s.get("coaching_recommendations", [])
        for r in recs:
            if any(kw in r.lower() for kw in ("cross-sell", "upsell", "opportunity", "peluang")):
                missed_opps += 1

    return {
        "count": count,
        "avg_overall": round(avg_overall, 1),
        "avg_script": round(avg_script, 1),
        "avg_compliance": round(avg_compliance, 1),
        "avg_sentiment": round(avg_sentiment, 1),
        "outcomes": outcomes,
        "top_violations": [{"rule_id": r, "count": c} for r, c in top_violations],
        "agent_ranking": agent_ranking[:10],
        "cross_sell_missed": missed_opps,
    }
