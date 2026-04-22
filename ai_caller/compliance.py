"""Compliance rule engine.

Runs a declarative rule pack (JSON) against a live or completed call transcript.
Supports two detection modes:

- regex_any: fast, deterministic, runs in the live Copilot loop (<10ms). Fires
  flags for pressure tactics, trigger-phrase coverage checks, forbidden claims.

- llm: context-aware, runs in the QA engine post-call (or deferred Copilot batch).
  Used for judgment calls like "did the consumer opt out and did the agent respect it".

Same engine design is re-used for PDPA healthcare rules in the Bloom pivot. The
engine knows nothing about PIAM or PDPA — it just executes rule JSON.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from llm import stream_chat

COMPLIANCE_DIR = Path(__file__).parent / "compliance"


@dataclass
class ComplianceFlag:
    """A single compliance finding on a call."""
    rule_id: str
    title: str
    status: Literal["pending", "satisfied", "fired"]
    severity: Literal["low", "medium", "high", "critical"]
    evidence: str | None = None
    turn_idx: int | None = None  # Position in transcript where flag fired/satisfied

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "status": self.status,
            "severity": self.severity,
            "evidence": self.evidence,
            "turn_idx": self.turn_idx,
        }


@dataclass
class CompliancePack:
    """Loaded compliance rule pack."""
    pack_id: str
    description: str
    rules: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, pack_id: str) -> "CompliancePack":
        path = COMPLIANCE_DIR / f"{pack_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Compliance pack not found: {pack_id}")
        with open(path) as f:
            data = json.load(f)
        return cls(
            pack_id=data["pack_id"],
            description=data.get("description", ""),
            rules=data.get("rules", []),
        )

    def initial_flags(self) -> list[ComplianceFlag]:
        """Return every rule as an unfulfilled flag, ready for live tracking."""
        return [
            ComplianceFlag(
                rule_id=r["id"],
                title=r["title"],
                status="pending",
                severity=r.get("severity_on_miss", "medium"),
            )
            for r in self.rules
        ]


class LiveComplianceTracker:
    """Tracks compliance rule satisfaction over a live call.

    Called once per final transcript turn. Runs fast (regex-only) checks live;
    LLM checks are deferred to `final_audit()` at call end.

    Designed for <10ms per turn so it never blocks the Copilot loop.
    """

    def __init__(self, pack: CompliancePack):
        self.pack = pack
        self.flags: dict[str, ComplianceFlag] = {
            f.rule_id: f for f in pack.initial_flags()
        }
        self.transcript: list[dict] = []
        self._product_discussion_started = False

    def on_turn(self, role: str, text: str) -> list[ComplianceFlag]:
        """Process one turn. Returns any flags that changed state this turn.

        `role` is "agent" or "user" (customer).
        `text` is the final transcript text for this turn.
        """
        turn_idx = len(self.transcript)
        self.transcript.append({"role": role, "text": text, "turn_idx": turn_idx})
        changed: list[ComplianceFlag] = []

        for rule in self.pack.rules:
            rule_id = rule["id"]
            detection = rule.get("detection", {})
            dtype = detection.get("type")

            flag = self.flags[rule_id]
            # Don't re-evaluate rules already resolved
            if flag.status in ("satisfied", "fired"):
                continue

            result = None
            if dtype == "regex_any":
                result = self._check_regex_rule(rule, role, text, turn_idx)
            elif dtype == "first_n_turns_must_contain":
                # This rule type requires checking at the boundary between
                # "still within grace window" and "grace window expired", so
                # it runs on every turn regardless of who spoke.
                result = self._check_first_n_turns_rule(rule, turn_idx)
            # LLM rules remain deferred to final_audit().

            if result:
                status, evidence = result
                flag.status = status
                flag.evidence = evidence
                flag.turn_idx = turn_idx
                changed.append(flag)

        return changed

    def _check_regex_rule(
        self, rule: dict, role: str, text: str, turn_idx: int
    ) -> tuple[str, str] | None:
        """Run a regex-type rule against this turn. Returns (status, evidence) if
        the rule changed state this turn, else None.
        """
        detection = rule["detection"]

        # Product-discussion / disclosure rules are role-agnostic by design:
        # during a warm-transferred call the same human drives both personas
        # through one mic, so STT tags everything as "user". The semantic rule
        # is "if anyone on the call brings up the product, someone must disclose
        # the effective rate" — it does not matter who said what.
        is_product_rule = "triggers_product_discussion" in detection
        if not is_product_rule:
            context_role = detection.get("context", "agent")
            if role != context_role:
                return None

        text_lower = text.lower()
        fire_on = rule.get("fire_on", "trigger_matched")

        # Case 1: simple trigger match → fire
        if "triggers_any" in detection and fire_on == "trigger_matched":
            for pattern in detection["triggers_any"]:
                if re.search(pattern, text_lower):
                    # Check exceptions
                    exceptions = detection.get("exception_if_accompanied_by", [])
                    if any(ex.lower() in text_lower for ex in exceptions):
                        continue
                    return ("fired", f"'{text}' matched forbidden pattern '{pattern}'")
            return None

        # Case 2: triggers_any with exception filter
        if (
            "triggers_any" in detection
            and fire_on == "trigger_matched_without_exception"
        ):
            for pattern in detection["triggers_any"]:
                if re.search(pattern, text_lower):
                    exceptions = detection.get("exception_if_accompanied_by", [])
                    if any(ex.lower() in text_lower for ex in exceptions):
                        continue
                    return ("fired", f"'{text}' matched '{pattern}' without exception")
            return None

        # Case 3: triggered/follow-up rule (product discussion disclosure).
        # Role-agnostic: trigger fires if anyone mentions the product, and the
        # fulfillment check scans all subsequent turns (not just agent turns)
        # because in Scenario B the human closer speaks through the caller mic,
        # so STT tags their disclosure as role="user".
        if "triggers_product_discussion" in detection:
            triggers = detection["triggers_product_discussion"]
            flag = self.flags[rule["id"]]
            trigger_turn = getattr(flag, "_trigger_turn", None)

            if trigger_turn is None and any(t.lower() in text_lower for t in triggers):
                self._product_discussion_started = True
                flag._trigger_turn = turn_idx  # type: ignore[attr-defined]
                trigger_turn = turn_idx

            if trigger_turn is not None:
                must_contain = detection.get("must_contain_within_next_3_turns_any", [])
                # Check every turn (any role) from trigger through now for fulfillment
                joined = " | ".join(
                    t["text"].lower() for t in self.transcript[trigger_turn : turn_idx + 1]
                )
                for pattern in must_contain:
                    if re.search(pattern, joined):
                        return ("satisfied", f"Disclosure found: '{text}'")
                # Not yet fulfilled; fire once 3 turns have passed without coverage
                turns_since = turn_idx - trigger_turn
                if turns_since >= 3:
                    return (
                        "fired",
                        "Product terms discussed but no effective-rate disclosure in 3 turns",
                    )

        return None

    def _check_first_n_turns_rule(
        self, rule: dict, turn_idx: int
    ) -> tuple[str, str] | None:
        """Evaluate a ``first_n_turns_must_contain`` rule at each turn.

        Semantics: within the first ``window_turns`` turns of ``context``
        role, at least one pattern in ``patterns_any`` must appear. If yes,
        the rule is satisfied. If the window has elapsed with no match, the
        rule fires.

        Used for AI identity disclosure (the "I'm an AI assistant" line
        that must happen in the first N agent turns, per docs/developer_plan.md
        §2 C and §4.2). Role-aware because only the *agent's* own
        turns count toward the window — the customer saying "are you an AI?"
        doesn't satisfy it on the agent's behalf.
        """
        detection = rule["detection"]
        patterns = detection.get("patterns_any", [])
        if not patterns:
            return None

        window = int(detection.get("window_turns", 3))
        context_role = detection.get("context", "agent")

        role_turns = [
            t for t in self.transcript if t["role"] == context_role
        ]
        if not role_turns:
            # Haven't heard from this role yet — can't evaluate either way
            return None

        considered = role_turns[:window]
        joined = " | ".join(t["text"].lower() for t in considered)
        for pattern in patterns:
            if re.search(pattern, joined):
                evidence_turn = next(
                    (t for t in considered if re.search(pattern, t["text"].lower())),
                    considered[0],
                )
                return ("satisfied", f"Disclosure heard: '{evidence_turn['text']}'")

        if len(role_turns) >= window:
            return (
                "fired",
                f"No AI-identity disclosure in first {window} {context_role} turns",
            )
        return None

    async def final_audit(self) -> list[ComplianceFlag]:
        """Run all remaining LLM-based rules on the full transcript.
        Returns the complete flag list.
        """
        for rule in self.pack.rules:
            flag = self.flags[rule["id"]]
            detection = rule.get("detection", {})

            dtype = detection.get("type")
            if dtype != "llm":
                # For regex rules still "pending", treat as satisfied if required
                # by intent (e.g. identity disclosure present somewhere in transcript)
                if flag.status == "pending" and rule["id"] in (
                    "identity_disclosure",
                ):
                    flag.status = (
                        "satisfied"
                        if self._agent_disclosed_identity()
                        else "fired"
                    )
                # A first_n_turns rule that's still pending at call end means
                # the call ended before the window was consumed. If no match
                # was ever heard, fire it; otherwise leave satisfied.
                elif flag.status == "pending" and dtype == "first_n_turns_must_contain":
                    patterns = detection.get("patterns_any", [])
                    context_role = detection.get("context", "agent")
                    joined = " | ".join(
                        t["text"].lower()
                        for t in self.transcript if t["role"] == context_role
                    )
                    matched = any(re.search(p, joined) for p in patterns)
                    flag.status = "satisfied" if matched else "fired"
                    if not matched:
                        flag.evidence = (
                            f"Call ended without required disclosure ({context_role})"
                        )
                continue

            if flag.status in ("satisfied", "fired"):
                continue

            result = await self._run_llm_detection(rule)
            if result is not None:
                fired, evidence = result
                flag.status = "fired" if fired else "satisfied"
                flag.evidence = evidence

        return list(self.flags.values())

    def _agent_disclosed_identity(self) -> bool:
        """Heuristic: did the agent say their name AND a company name in first 3 turns?"""
        agent_turns = [t["text"] for t in self.transcript if t["role"] == "agent"][:3]
        joined = " ".join(agent_turns).lower()
        has_self_intro = any(w in joined for w in ("this is", "saya", "i'm", "my name"))
        has_company = any(w in joined for w in ("from", "dari", "representing"))
        return has_self_intro and has_company

    async def _run_llm_detection(self, rule: dict) -> tuple[bool, str] | None:
        """Use LLM as judge for context-sensitive rules."""
        detection = rule["detection"]
        prompt = detection.get("prompt", "")
        transcript_text = "\n".join(
            f"{t['role'].upper()}: {t['text']}" for t in self.transcript
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict compliance auditor for Malaysian financial "
                    "telemarketing calls under BNM and PIAM guidelines. Return "
                    "ONLY valid JSON with exactly the keys requested — no prose."
                ),
            },
            {
                "role": "user",
                "content": f"TRANSCRIPT:\n{transcript_text}\n\nQUESTION: {prompt}",
            },
        ]

        response_text = ""

        async def collect(chunk: str):
            nonlocal response_text
            response_text += chunk

        try:
            # Compliance LLM rules return small JSON ({fired, evidence}) but
            # evidence quotes can run long; 600 gives plenty of headroom.
            await stream_chat(messages, collect, max_tokens=600)
        except Exception as e:
            print(f"[COMPLIANCE] LLM error on {rule['id']}: {e}")
            return None

        # Strip markdown code fences if LLM wraps JSON in ```
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"[COMPLIANCE] Non-JSON LLM response on {rule['id']}: {response_text[:200]}")
            return None

        # Interpret rule-specific result keys
        rule_id = rule["id"]
        evidence = data.get("evidence") or ""

        if rule_id == "recording_consent":
            fired = not data.get("fired", False) if "fired" in data else False
            # rule: fired=true means agent DID mention consent. Invert: fired flag
            # on the tracker means the agent FAILED to get consent.
            return (not data.get("fired", False), evidence)
        if rule_id == "opt_out_handling":
            opted_out = data.get("consumer_opted_out", False)
            respected = data.get("agent_respected", True)
            if not opted_out:
                return (False, "N/A — customer did not opt out")
            return (not respected, evidence)
        if rule_id == "third_party_consent":
            third = data.get("third_party_answered", False)
            leaked = data.get("agent_leaked", False)
            if not third:
                return (False, "N/A — account holder answered")
            return (leaked, evidence)
        if rule_id == "ai_scope_boundary":
            exceeded = data.get("exceeded_scope", False)
            return (exceeded, evidence)

        # Default: "fired" means the rule was violated
        return (data.get("fired", False), evidence)

    def snapshot(self) -> dict:
        """Return current state for UI rendering."""
        return {
            "pack_id": self.pack.pack_id,
            "flags": [f.to_dict() for f in self.flags.values()],
            "turn_count": len(self.transcript),
        }
