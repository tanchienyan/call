"""Warm-transfer mechanism.

Handles the AI → human handoff. Two paths:

1. Browser demo: when the AI agent emits "[TRANSFER_TO_HUMAN]" in its response,
   we intercept it before TTS, fire a `transfer_initiated` event on the Copilot
   bus, and the UI shows a "human closer picked up" banner. The human then
   speaks through the same WebSocket (or a second "closer" browser tab).

2. Real Twilio call: the AI's Twilio leg gets moved into a conference. A
   separate outbound leg calls the human closer's phone/softphone and joins
   the conference. The AI can drop or stay as listener. This is the Twilio
   `<Dial><Conference>` pattern with programmatic participant management.

For the April demo, path #1 is the primary path — it's deterministic and
doesn't depend on Twilio conference quirks. Path #2 is built and plugged in
but kept off the critical demo path per demo.md §5 risk #3.
"""
from __future__ import annotations

import re
from typing import Optional

from twilio.rest import Client
import config
import copilot as copilot_mod

TRANSFER_MARKER = "[TRANSFER_TO_HUMAN]"
_marker_re = re.compile(re.escape(TRANSFER_MARKER), re.IGNORECASE)


def extract_transfer_signal(agent_text: str) -> tuple[bool, str]:
    """Check if the agent response contains the transfer marker.
    Returns (should_transfer, cleaned_text).
    """
    if _marker_re.search(agent_text):
        cleaned = _marker_re.sub("", agent_text).strip()
        return True, cleaned
    return False, agent_text


def publish_transfer_event(call_id: str, to_agent: str = "Edison (Human Closer)"):
    """Announce on the Copilot bus that a warm transfer is happening.
    The Copilot UI listens and switches its header to indicate human-in-the-loop.
    """
    bus = copilot_mod.get_or_create_bus(call_id)
    bus.publish({
        "type": "transfer_initiated",
        "to": to_agent,
        "message": f"AI qualified interest. Warm-transferring to {to_agent}.",
    })


# ─── Twilio conference-based transfer ───

def _twilio_client() -> Client:
    if config.TWILIO_API_KEY_SID:
        return Client(
            config.TWILIO_API_KEY_SID,
            config.TWILIO_API_KEY_SECRET,
            config.TWILIO_ACCOUNT_SID,
        )
    return Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


def move_call_to_conference(
    twilio_call_sid: str, conference_name: str, ai_stays_as_listener: bool = False
) -> dict:
    """Move an active Twilio call into a named conference room.

    For warm transfer: the active customer leg is updated with new TwiML that
    places them in the conference room. We then separately dial out to the
    human closer and join them to the same conference. The AI can either drop
    (default) or stay muted as a listener for QA.
    """
    client = _twilio_client()
    conference_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Conference
            startConferenceOnEnter="true"
            endConferenceOnExit="false"
            waitUrl=""
        >{conference_name}</Conference>
    </Dial>
</Response>"""

    call = client.calls(twilio_call_sid).update(twiml=conference_twiml)
    return {"ok": True, "call_sid": call.sid, "conference": conference_name}


def dial_human_closer(human_phone: str, conference_name: str) -> dict:
    """Dial out to the human closer and put them straight into the conference."""
    client = _twilio_client()
    conference_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connecting you to the qualified caller now.</Say>
    <Dial>
        <Conference startConferenceOnEnter="true" endConferenceOnExit="true">
            {conference_name}
        </Conference>
    </Dial>
</Response>"""

    call = client.calls.create(
        to=human_phone,
        from_=config.TWILIO_PHONE_NUMBER,
        twiml=conference_twiml,
    )
    return {"ok": True, "sid": call.sid, "to": human_phone}
