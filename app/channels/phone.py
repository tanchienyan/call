"""Phone channel — Retell AI outbound calls with IVR navigation."""

import httpx
import asyncio
import time
from datetime import datetime
from ..config import settings

RETELL_API = "https://api.retellai.com"
AGENT_ID = "agent_a8ede5afc28f6ed16682a94e75"
FROM_NUMBER = "+12012318503"


async def make_call(to_number: str, persona: dict = None, context: dict = None) -> dict:
    """Make an outbound mystery shopping phone call.
    
    Returns dict with: call_id, status, duration_seconds, transcript,
    recording_url, cost_cents, analysis
    """
    headers = {
        "Authorization": f"Bearer {settings.RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        # Initiate outbound call
        resp = await client.post(f"{RETELL_API}/v2/create-phone-call", headers=headers, json={
            "agent_id": AGENT_ID,
            "from_number": FROM_NUMBER,
            "to_number": to_number,
        })
        data = resp.json()
        call_id = data.get("call_id")

        if not call_id:
            return {"error": data.get("message", str(data)), "status": "failed"}

    # Poll for completion (max 10 min for IVR + hold + conversation)
    result = await _poll_call(call_id, headers, max_wait=600)
    return result


async def make_web_call() -> dict:
    """Create a web call for browser-based testing."""
    headers = {
        "Authorization": f"Bearer {settings.RETELL_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{RETELL_API}/v2/create-web-call", headers=headers, json={
            "agent_id": AGENT_ID,
        })
        return resp.json()


async def get_call_status(call_id: str) -> dict:
    """Get current status of a call."""
    headers = {"Authorization": f"Bearer {settings.RETELL_API_KEY}"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{RETELL_API}/v2/get-call/{call_id}", headers=headers)
        return resp.json()


async def list_calls(limit: int = 20) -> list:
    """List recent calls."""
    headers = {
        "Authorization": f"Bearer {settings.RETELL_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{RETELL_API}/v2/list-calls", headers=headers, json={
            "limit": limit,
            "sort_order": "descending",
        })
        return resp.json()


async def update_agent_prompt(prompt: str, begin_message: str = None):
    """Update the agent's LLM prompt."""
    headers = {
        "Authorization": f"Bearer {settings.RETELL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"general_prompt": prompt}
    if begin_message:
        payload["begin_message"] = begin_message

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{RETELL_API}/update-retell-llm/llm_ebd65462dc353925430ea29eaa7c",
            headers=headers, json=payload,
        )
        return resp.json()


async def _poll_call(call_id: str, headers: dict, max_wait: int = 600) -> dict:
    """Poll a call until it ends, then return full details."""
    elapsed = 0
    async with httpx.AsyncClient(timeout=10) as client:
        while elapsed < max_wait:
            await asyncio.sleep(5)
            elapsed += 5
            try:
                resp = await client.get(f"{RETELL_API}/v2/get-call/{call_id}", headers=headers)
                data = resp.json()
                status = data.get("call_status", "")
                if status in ("ended", "error"):
                    return _format_call_result(data)
            except Exception:
                pass

    # Timeout — get whatever we have
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{RETELL_API}/v2/get-call/{call_id}", headers=headers)
            return _format_call_result(resp.json())
    except Exception:
        return {"call_id": call_id, "status": "timeout", "error": "Call polling timed out"}


def _format_call_result(data: dict) -> dict:
    """Extract clean result from Retell API response."""
    cost = data.get("call_cost", {})
    analysis = data.get("call_analysis", {})
    return {
        "call_id": data.get("call_id", ""),
        "status": data.get("call_status", "unknown"),
        "duration_seconds": data.get("duration_ms", 0) / 1000,
        "transcript": data.get("transcript", ""),
        "recording_url": data.get("recording_url", ""),
        "cost_cents": cost.get("combined_cost", 0),
        "disconnection_reason": data.get("disconnection_reason", ""),
        "analysis": {
            "summary": analysis.get("call_summary", ""),
            "sentiment": analysis.get("user_sentiment", ""),
            "successful": analysis.get("call_successful", False),
        },
        "latency": data.get("latency", {}),
    }
