"""DEMO-ONLY synthetic call transcript generator.

⚠️  IMPORTANT (docs/developer_plan.md §4.5): Every row inserted by this script is
tagged with ``is_synthetic=1`` on the ``calls`` table. These rows exist only
to populate the fleet dashboard for live demos — they are NOT real calls and
MUST NEVER be exported as part of the conversation corpus, used as fine-tune
training data, or shown in customer-facing metrics. All corpus-export queries
(``storage.list_calls_with_labels``) exclude synthetic rows by default.

Generates N plausible credit-card balance-transfer call transcripts in Bahasa
+ English code-switched Malaysian telemarketing register. Each call has:

- Varied outcome distribution (converted, qualified, declined, voicemail,
  wrong_number, callback) roughly matching real BPO campaign stats
- Labeled synthetic agent (Agent_A, Agent_B, ... Agent_E) with intentional
  performance variance so the fleet dashboard has a meaningful ranking
- Intentional compliance violations seeded in ~15% of calls so top-violation
  lists are populated
- Campaign label "UTS-Sample-Campaign-2026-04"

Run once before the demo:
    python synth_data.py --count 100

This writes to data/calls.db as calls with agent_scenario="uts_bt_synth" and
``is_synthetic=1``, plus a precomputed scorecard in the summary column so the
fleet dashboard loads instantly without re-running LLM calls.

For the demo: 100 calls is plenty. 500 looks more impressive but is 5x LLM
cost. Decided in docs/plan.md §18 decision #4.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
import uuid
from datetime import datetime, timedelta

from llm import stream_chat
import storage
from qa_engine import get_engine


# Outcome distribution for a realistic outbound campaign
OUTCOME_WEIGHTS = {
    "converted": 0.08,      # 8% — human closer wins after transfer
    "qualified": 0.12,      # 12% — AI qualified + transferred, outcome pending
    "declined": 0.35,       # 35% — not interested
    "callback": 0.10,       # 10% — busy, callback requested
    "voicemail": 0.20,      # 20% — no answer, left VM
    "wrong_number": 0.08,   # 8% — wrong person
    "other": 0.07,          # 7% — weird outcomes
}

SYNTH_AGENTS = [
    {"name": "Agent_Aminah", "perf_bias": 0.15},   # best performer
    {"name": "Agent_Hafiz", "perf_bias": 0.05},
    {"name": "Agent_Siti", "perf_bias": 0.0},
    {"name": "Agent_Razif", "perf_bias": -0.05},
    {"name": "Agent_Marina", "perf_bias": -0.15},  # underperformer
]


GENERATION_PROMPT_TEMPLATE = """Generate a realistic Malaysian outbound telemarketing call transcript in Bahasa Malaysia + English code-switched style (natural Manglish register used by Malaysian call-center agents).

Context:
- Agent: Nurul from MayFirst Bank Card Services
- Product: Credit-card balance-transfer offer (3.5% for 12 months)
- Customer: Puan {customer_name} (or Encik for male)
- Outcome target: {outcome}
- Performance quality: {quality_desc}

Turn format: alternating AGENT and USER turns. Use Bahasa with natural English code-switching like real Malaysian outbound scripts. Example: "Puan, saya nak offer one balance transfer plan..."

Rules:
- 6-18 turns total depending on outcome
- Agent must sound human (uses "actually", "sebenarnya", "okay lah", natural fillers)
- Customer responses should be realistic for the outcome
- If outcome is "voicemail": only 1-2 agent turns, no user responses
- If outcome is "wrong_number": customer says wrong person in turn 2-3
- If outcome is "declined": customer politely refuses
- If outcome is "converted" or "qualified": customer shows interest, agent transfers

Performance quality adjustment:
{quality_instructions}

Return ONLY JSON array of turns: [{{"role": "agent", "text": "..."}}, {{"role": "user", "text": "..."}}, ...]
No prose, no markdown. Use Malaysian names, natural speech."""


QUALITY_INSTRUCTIONS = {
    "excellent": (
        "Agent executes perfectly: opens with AI-identity disclosure in turn 1 "
        "(e.g. 'saya pembantu AI dari MayFirst' / 'I'm an AI assistant from…'), "
        "full opening, recording consent, effective-rate disclosure, no pressure, "
        "handles objections well."
    ),
    "good": (
        "Agent discloses AI identity in first 2 turns. Does most beats well but "
        "may forget recording consent OR effective-rate disclosure ONCE."
    ),
    "mediocre": (
        "Agent may or may not disclose AI identity. Misses recording consent OR "
        "rushes pitch without disclosure. May interrupt customer."
    ),
    "poor": (
        "Agent does NOT disclose AI identity. Skips recording consent AND "
        "effective-rate disclosure. Uses mild pressure tactics like 'hari ini "
        "sahaja' or 'last chance'. Doesn't respect opt-out quickly."
    ),
}


MALAY_NAMES = [
    "Aminah", "Siti Zahra", "Nur Aisyah", "Fatimah", "Hafizah",
    "Ahmad", "Hafiz", "Razif", "Syafiq", "Azizul",
    "Marina", "Kamariah", "Rosmah", "Zaiton", "Halimah",
    "Faizal", "Khairul", "Zulkifli", "Mohd Fadzil", "Rahman",
]


def pick_outcome() -> str:
    r = random.random()
    acc = 0
    for outcome, weight in OUTCOME_WEIGHTS.items():
        acc += weight
        if r <= acc:
            return outcome
    return "other"


def pick_quality(agent_bias: float) -> str:
    """Agent-specific quality distribution biased by perf_bias."""
    r = random.random() + agent_bias
    if r > 0.7: return "excellent"
    if r > 0.4: return "good"
    if r > 0.15: return "mediocre"
    return "poor"


async def generate_transcript(customer_name: str, outcome: str, quality: str) -> list[dict]:
    """Generate a single synthetic transcript via LLM."""
    prompt = GENERATION_PROMPT_TEMPLATE.format(
        customer_name=customer_name,
        outcome=outcome,
        quality_desc=quality,
        quality_instructions=QUALITY_INSTRUCTIONS[quality],
    )
    messages = [
        {"role": "system", "content": "You generate realistic Malaysian outbound telemarketing call transcripts for training/evaluation data. Return only JSON."},
        {"role": "user", "content": prompt},
    ]

    collected = ""
    async def collect(chunk):
        nonlocal collected
        collected += chunk

    # Transcript JSON arrays can exceed the live-call 300-token default.
    # Budget 2000 so 18-turn calls fit without truncation → no "Bad JSON" loss.
    await stream_chat(messages, collect, max_tokens=2000)

    # Strip code fences
    import re as _re
    cleaned = collected.strip()
    if cleaned.startswith("```"):
        cleaned = _re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=_re.MULTILINE)

    try:
        turns = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[SYNTH] Bad JSON: {collected[:150]}")
        return []

    if not isinstance(turns, list):
        return []

    # Add timestamps
    now = datetime.utcnow()
    for i, t in enumerate(turns):
        t["ts"] = (now + timedelta(seconds=i * 6)).isoformat()

    return turns


async def generate_one_call(seq: int, compliance_pack_id: str = "piam_consumer_credit_v0") -> dict:
    """Generate one synthetic call end-to-end: transcript + scored + stored."""
    outcome = pick_outcome()
    agent_info = random.choice(SYNTH_AGENTS)
    quality = pick_quality(agent_info["perf_bias"])
    customer_name = random.choice(MALAY_NAMES)

    print(f"[SYNTH {seq:03d}] {agent_info['name']} | {outcome} | {quality} | {customer_name}")

    transcript = await generate_transcript(customer_name, outcome, quality)
    if not transcript:
        return {"ok": False, "reason": "empty_transcript"}

    call_id = f"synth_{uuid.uuid4().hex[:12]}"
    duration = max(20, sum(len(t.get("text", "").split()) for t in transcript) * 0.45)

    # Insert into DB with the synthetic tag so corpus-export queries and
    # real-fleet aggregates can safely exclude these rows.
    storage.create_call(
        call_id=call_id,
        to_number=f"+60{random.randint(100000000, 999999999)}",
        from_number="+60312345678",
        agent_name=agent_info["name"],
        agent_scenario="uts_bt_synth",
        voice_id="synth",
        brand_id="uts_insurance",
        channel="voice",
        language="multi",
        is_synthetic=True,
    )
    storage.update_call(
        call_id,
        status="completed",
        transcript=transcript,
        duration_seconds=round(duration, 1),
        started_at=datetime.utcnow().isoformat(),
        ended_at=datetime.utcnow().isoformat(),
    )
    # Ground-truth outcome label on the column itself (QA engine would
    # overwrite with outcome_source='qa_engine', which is fine — either
    # way the `outcome` column is populated for fleet queries).
    storage.set_labels(
        call_id,
        outcome=outcome,
        outcome_source="synth",
        language="multi",
        brand_id="uts_insurance",
    )

    # Score it
    engine = get_engine()
    try:
        scorecard = await engine.score_call(call_id, compliance_pack_id=compliance_pack_id)
        sc_dict = scorecard.to_dict()
        sc_dict["synthetic_agent"] = agent_info["name"]
        sc_dict["quality_label"] = quality  # Ground truth for calibration
        sc_dict["campaign"] = "UTS-Sample-Campaign-2026-04"
        storage.update_call(call_id, summary=json.dumps(sc_dict, ensure_ascii=False))
        return {"ok": True, "call_id": call_id, "outcome": outcome, "score": scorecard.overall_score}
    except Exception as e:
        print(f"[SYNTH {seq:03d}] Scoring failed: {e}")
        return {"ok": False, "reason": str(e)}


async def generate_fleet(count: int, parallelism: int = 5):
    """Generate `count` calls with bounded parallelism (avoids LLM rate limits)."""
    print(f"[SYNTH] Generating {count} calls with parallelism={parallelism}")
    t0 = time.monotonic()

    results = []
    sem = asyncio.Semaphore(parallelism)

    async def guarded(seq):
        async with sem:
            return await generate_one_call(seq)

    tasks = [asyncio.create_task(guarded(i)) for i in range(count)]
    for i, task in enumerate(asyncio.as_completed(tasks)):
        r = await task
        results.append(r)
        if (i + 1) % 10 == 0:
            print(f"[SYNTH] Progress: {i+1}/{count}")

    ok = sum(1 for r in results if r.get("ok"))
    elapsed = time.monotonic() - t0
    print(f"[SYNTH] Done. {ok}/{count} ok in {elapsed:.0f}s")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--parallelism", type=int, default=5)
    args = p.parse_args()
    asyncio.run(generate_fleet(args.count, args.parallelism))


if __name__ == "__main__":
    main()
