"""Phone call channel via Retell AI API."""

import httpx
import json
import time
from datetime import datetime
from ..config import config
from ..orchestrator.journey import StepResult, StepStatus, JourneyStep


RETELL_API = "https://api.retellai.com"


async def phone_call(step: JourneyStep, context: dict) -> StepResult:
    """Make an AI mystery shopping phone call via Retell."""
    result = StepResult(
        step_name=step.name,
        step_type=step.step_type,
        started_at=datetime.now(),
    )

    phone_number = step.config.get("phone_number", "")
    if not phone_number:
        result.status = StepStatus.FAILED
        result.notes = "No phone number provided"
        return result

    api_key = config.RETELL_API_KEY
    if not api_key:
        result.status = StepStatus.FAILED
        result.notes = "RETELL_API_KEY not configured"
        return result

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Build dynamic prompt incorporating context from previous steps
    extra_context = ""
    step_results = context.get("step_results", {})
    if step.config.get("reference_previous"):
        if "Email Inquiry" in step_results:
            extra_context += "\nYou previously sent an email inquiry. You can mention 'I also sent an email earlier' if it feels natural."
        if "Webchat Inquiry" in step_results:
            extra_context += "\nYou previously chatted on the website. You can mention 'I was chatting on your website earlier' if appropriate."

    persona = context.get("persona", {})
    target = context.get("target", {})

    prompt = f"""You are {persona.get('name', 'Sarah Mitchell')}, calling {target.get('name', 'the hotel')} to inquire about a room booking.

Style: {persona.get('style', 'Professional and polite')}
{extra_context}

You want:
- Dates: next Thursday to Sunday (3 nights)
- Room: quiet, high floor
- Purpose: tech conference
- Interested in: late checkout, gym, WiFi

Be natural and conversational. Use fillers. Keep the call under 3 minutes.
End by asking them to email you the details."""

    print(f"   📞 Calling {phone_number}...")

    try:
        # Create or update LLM with context
        llm_resp = httpx.post(f"{RETELL_API}/create-retell-llm", headers=headers, json={
            "model": "gpt-4o",
            "general_prompt": prompt,
            "begin_message": f"Hi there, I'm hoping you can help me. I'm looking to book a room at your hotel for next week.",
        }, timeout=15)
        llm_data = llm_resp.json()
        llm_id = llm_data.get("llm_id")

        if not llm_id:
            result.status = StepStatus.FAILED
            result.notes = f"Failed to create LLM: {llm_data}"
            return result

        # Create agent
        agent_resp = httpx.post(f"{RETELL_API}/create-agent", headers=headers, json={
            "agent_name": f"Mystery Shopper - {persona.get('name', 'Sarah')}",
            "voice_id": "11labs-Willa",
            "language": "en-GB",
            "response_engine": {"type": "retell-llm", "llm_id": llm_id},
            "enable_backchannel": True,
            "ambient_sound": "coffee-shop",
            "ambient_sound_volume": 0.3,
        }, timeout=15)
        agent_data = agent_resp.json()
        agent_id = agent_data.get("agent_id")

        if not agent_id:
            result.status = StepStatus.FAILED
            result.notes = f"Failed to create agent: {agent_data}"
            return result

        # Make the call
        call_resp = httpx.post(f"{RETELL_API}/v2/create-phone-call", headers=headers, json={
            "agent_id": agent_id,
            "to_number": phone_number,
            "from_number": config.RETELL_FROM_NUMBER if hasattr(config, 'RETELL_FROM_NUMBER') else None,
        }, timeout=15)
        call_data = call_resp.json()
        call_id = call_data.get("call_id")

        if not call_id:
            # Might not have a phone number — try web call for demo
            print(f"   ⚠️  Can't make phone call (no from_number). Creating web call for demo...")
            call_resp = httpx.post(f"{RETELL_API}/v2/create-web-call", headers=headers, json={
                "agent_id": agent_id,
            }, timeout=15)
            call_data = call_resp.json()
            call_id = call_data.get("call_id")
            result.notes = "Web call created (no phone number available for outbound)"
            result.data_sent = f"Web call ID: {call_id}"
            result.status = StepStatus.COMPLETED
            result.completed_at = datetime.now()
            result.context_for_next = {"call_id": call_id, "agent_id": agent_id}
            return result

        print(f"   📞 Call initiated: {call_id}")

        # Poll for completion
        max_wait = 300
        elapsed = 0
        while elapsed < max_wait:
            time.sleep(5)
            elapsed += 5
            status_resp = httpx.get(f"{RETELL_API}/v2/get-call/{call_id}", headers=headers, timeout=10)
            if status_resp.status_code == 200:
                call_status = status_resp.json()
                if call_status.get("call_status") in ["ended", "error"]:
                    break

        # Get final call details
        final_resp = httpx.get(f"{RETELL_API}/v2/get-call/{call_id}", headers=headers, timeout=10)
        final_data = final_resp.json()

        transcript = final_data.get("transcript", "")
        duration = final_data.get("call_duration_ms", 0) / 1000

        result.status = StepStatus.COMPLETED
        result.completed_at = datetime.now()
        result.data_received = transcript
        result.response_time_seconds = duration
        result.notes = f"Call completed. Duration: {duration:.0f}s"
        result.context_for_next = {"call_transcript": transcript, "call_id": call_id}

        print(f"   ✅ Call completed ({duration:.0f}s)")

    except Exception as e:
        result.status = StepStatus.FAILED
        result.notes = str(e)
        print(f"   ❌ Error: {e}")

    return result
