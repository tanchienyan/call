"""Live Copilot for human closers.

Subscribes to a call's real-time transcript stream. For each final turn it:

1. Runs the coaching-card trigger engine (regex on lowercased text) and emits
   any matched cards with <10ms latency.
2. Feeds the turn to the LiveComplianceTracker and emits any state changes.
3. Re-publishes the transcript turn itself for UI rendering.

Designed as an in-process event bus so the CallSession writes events once and
all subscribers (Copilot UI, QA, recording) receive them without extra network
hops. This keeps the <2s "utterance → coaching card" budget achievable.

Architecture:
    CallSession._on_stt_transcript(final) ─┐
                                           ▼
                                    CopilotBus.publish()
                                           │
                      ┌────────────────────┼──────────────────────┐
                      ▼                    ▼                      ▼
               Coaching engine    Compliance tracker      Transcript tail
                      │                    │                      │
                      └──► events ────►────┴────►──── Copilot WebSocket UI
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from compliance import CompliancePack, LiveComplianceTracker

COACHING_DIR = Path(__file__).parent / "coaching"


# ─── Coaching card engine ───

@dataclass
class CoachingCardPack:
    pack_id: str
    cards: list[dict]

    @classmethod
    def load(cls, pack_id: str) -> "CoachingCardPack":
        path = COACHING_DIR / f"{pack_id}.json"
        with open(path) as f:
            data = json.load(f)
        return cls(pack_id=data["pack_id"], cards=data.get("cards", []))


class CoachingEngine:
    """Fires coaching cards based on trigger phrases in transcript turns.

    Regex-based, sub-10ms per turn. Each card fires at most once per call
    (unless explicitly marked repeatable), since agents don't need the same
    reminder twice.
    """

    def __init__(self, pack: CoachingCardPack):
        self.pack = pack
        self._fired_ids: set[str] = set()
        # Precompile triggers for speed
        self._compiled: dict[str, list[re.Pattern]] = {
            c["id"]: [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in c["triggers"]]
            for c in pack.cards
        }

    def on_turn(self, role: str, text: str) -> list[dict]:
        """Return cards to display for this turn (newly fired only)."""
        fired = []
        for card in self.pack.cards:
            card_id = card["id"]
            if card_id in self._fired_ids and not card.get("repeatable", False):
                continue
            # Respect role_filter if specified
            role_filter = card.get("role_filter")
            if role_filter and role != role_filter:
                continue
            for pattern in self._compiled[card_id]:
                if pattern.search(text):
                    self._fired_ids.add(card_id)
                    fired.append({
                        "type": "coaching_card",
                        "card_id": card_id,
                        "title": card["title"],
                        "suggestion": card["suggestion"],
                        "color": card.get("color", "blue"),
                        "triggered_by": text,
                        "triggered_role": role,
                        "ts": time.time(),
                    })
                    break
        return fired


# ─── Event bus ───

class CopilotBus:
    """Per-call event bus. Publishers push events; subscribers (WebSockets)
    receive them via async iterator.
    """

    def __init__(self, call_id: str):
        self.call_id = call_id
        self._subscribers: list[asyncio.Queue] = []
        self._history: list[dict] = []  # Replay buffer for late-joining subscribers
        self.created_at = time.time()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        # Replay history so late-joining UIs see the full context
        for event in self._history:
            q.put_nowait(event)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self, event: dict):
        event = {**event, "call_id": self.call_id}
        self._history.append(event)
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events for slow consumers rather than blocking


# Global bus registry — keyed by call_id
_buses: dict[str, CopilotBus] = {}


def get_or_create_bus(call_id: str) -> CopilotBus:
    if call_id not in _buses:
        _buses[call_id] = CopilotBus(call_id)
    return _buses[call_id]


def close_bus(call_id: str):
    _buses.pop(call_id, None)


# ─── Copilot session ───

class CopilotSession:
    """Drives coaching + compliance for a single call.

    Call `attach_to_call(call_session)` to register event handlers on an existing
    CallSession or WebCallSession. Runs alongside the call without interfering.
    """

    def __init__(
        self,
        call_id: str,
        coaching_pack_id: str | None = None,
        compliance_pack_id: str | None = None,
    ):
        self.call_id = call_id
        self.bus = get_or_create_bus(call_id)
        self.coaching: CoachingEngine | None = None
        self.compliance: LiveComplianceTracker | None = None

        if coaching_pack_id:
            try:
                pack = CoachingCardPack.load(coaching_pack_id)
                self.coaching = CoachingEngine(pack)
                print(f"[COPILOT {call_id}] Coaching pack loaded: {coaching_pack_id}")
            except Exception as e:
                print(f"[COPILOT {call_id}] Failed to load coaching pack {coaching_pack_id}: {e}")

        if compliance_pack_id:
            try:
                pack = CompliancePack.load(compliance_pack_id)
                self.compliance = LiveComplianceTracker(pack)
                print(f"[COPILOT {call_id}] Compliance pack loaded: {compliance_pack_id}")
                # Publish initial flag set so UI can render the checklist immediately
                self.bus.publish({
                    "type": "compliance_snapshot",
                    "snapshot": self.compliance.snapshot(),
                    "ts": time.time(),
                })
            except Exception as e:
                print(f"[COPILOT {call_id}] Failed to load compliance pack {compliance_pack_id}: {e}")

    def on_turn(self, role: str, text: str):
        """Called when a new final transcript turn appears on the call.

        Publishes transcript + any coaching cards + any compliance state changes
        to the bus. Returns quickly (target <10ms) so it never blocks the call.
        """
        t0 = time.monotonic()

        # 1. Transcript
        self.bus.publish({
            "type": "transcript",
            "role": role,
            "text": text,
            "ts": time.time(),
        })

        # 2. Coaching cards
        if self.coaching:
            for card in self.coaching.on_turn(role, text):
                self.bus.publish(card)

        # 3. Compliance
        if self.compliance:
            changed = self.compliance.on_turn(role, text)
            if changed:
                for flag in changed:
                    self.bus.publish({
                        "type": "compliance_update",
                        "flag": flag.to_dict(),
                        "ts": time.time(),
                    })

        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms > 50:
            print(f"[COPILOT {self.call_id}] Slow turn: {elapsed_ms:.1f}ms")

    async def finalize(self) -> dict:
        """Run deferred LLM compliance checks and publish final snapshot."""
        if not self.compliance:
            return {}
        print(f"[COPILOT {self.call_id}] Running final compliance audit...")
        t0 = time.monotonic()
        await self.compliance.final_audit()
        elapsed = (time.monotonic() - t0) * 1000
        snapshot = self.compliance.snapshot()
        self.bus.publish({
            "type": "compliance_final",
            "snapshot": snapshot,
            "audit_ms": round(elapsed, 0),
            "ts": time.time(),
        })
        print(f"[COPILOT {self.call_id}] Audit complete ({elapsed:.0f}ms)")
        return snapshot


# Global Copilot registry — keyed by call_id
_copilots: dict[str, CopilotSession] = {}


def attach_copilot(
    call_id: str, coaching_pack_id: str | None = None, compliance_pack_id: str | None = None
) -> CopilotSession:
    if call_id in _copilots:
        return _copilots[call_id]
    cp = CopilotSession(call_id, coaching_pack_id, compliance_pack_id)
    _copilots[call_id] = cp
    return cp


def get_copilot(call_id: str) -> CopilotSession | None:
    return _copilots.get(call_id)


def detach_copilot(call_id: str):
    _copilots.pop(call_id, None)
