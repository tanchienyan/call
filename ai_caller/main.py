"""AI Outbound Caller — FastAPI server with Twilio WebSocket integration."""
import json
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

import config
import storage
from caller import make_outbound_call
from pipeline import CallSession
from web_session import WebCallSession
from tts import list_voices
import copilot as copilot_mod
from qa_engine import get_engine as get_qa_engine, fleet_summary

app = FastAPI(title="AI Outbound Caller", version="1.0")

# Active call sessions
active_sessions: dict[str, CallSession] = {}
pending_agents: dict[str, dict] = {}  # call_id → prepared agent config

# Static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Agent + brand configs
AGENTS_DIR = Path(__file__).parent / "agents"
BRANDS_DIR = AGENTS_DIR / "brands"


def load_agents() -> dict:
    """Load all agent scenario configs from agents/*.json.

    Skips the brands/ subdirectory — those are tenant profiles, not agents.
    """
    agents = {}
    for f in AGENTS_DIR.glob("*.json"):
        with open(f) as fh:
            data = json.load(fh)
            agents[data["scenario"]] = data
    return agents


def load_brands() -> dict:
    """Load all brand/tenant profile configs from agents/brands/*.json.

    A brand profile provides default_variables, tone, default_voice_id, and
    optional location metadata that get merged onto any agent invoked under
    that brand_id. This is the seam for multi-tenant / multi-campaign use
    (developmentplan.md §4.4).
    """
    brands = {}
    if not BRANDS_DIR.exists():
        return brands
    for f in BRANDS_DIR.glob("*.json"):
        with open(f) as fh:
            data = json.load(fh)
            bid = data.get("brand_id") or f.stem
            brands[bid] = data
    return brands


def _interpolate(text: str, variables: dict) -> str:
    """Replace {{var}} placeholders and mark leftovers as not specified."""
    for var, val in variables.items():
        text = text.replace("{{" + var + "}}", str(val))
    return re.sub(r"\{\{[^}]+\}\}", "[not specified]", text)


def get_agent(scenario: str, variables: dict | None = None,
              brand_id: str | None = None) -> dict:
    """Get agent config with brand profile + template variables applied.

    Merge order (later overrides earlier):
    1. Agent JSON defaults
    2. Brand default_variables (if brand_id provided)
    3. Call-level variables from the request
    4. Overrides applied by callers (voice_id, system_prompt_override, etc.)

    Brand tone — if present — is prepended to the agent system_prompt as a
    standalone directive block so the agent can speak with the brand voice
    without touching every prompt in the repo.
    """
    agents = load_agents()
    if scenario not in agents:
        raise ValueError(f"Unknown scenario: {scenario}")

    agent = json.loads(json.dumps(agents[scenario]))  # deep copy
    variables = dict(variables or {})

    # Brand layer
    brand = None
    if brand_id:
        brands = load_brands()
        brand = brands.get(brand_id)
        if brand is None:
            raise ValueError(f"Unknown brand_id: {brand_id}")

        # Call-level variables win over brand defaults.
        merged = dict(brand.get("default_variables") or {})
        merged.update(variables)
        variables = merged

        # Prepend brand tone so it's first thing the model sees.
        tone = (brand.get("tone") or "").strip()
        if tone:
            agent["system_prompt"] = (
                f"# BRAND TONE ({brand.get('brand_name', brand_id)})\n{tone}\n\n"
                + agent.get("system_prompt", "")
            )

        # Brand default_voice_id is a fallback — agent's own voice wins.
        if not agent.get("voice_id"):
            default_vid = brand.get("default_voice_id")
            if default_vid:
                agent["voice_id"] = default_vid

        agent["brand_id"] = brand_id

    for key in ("system_prompt", "first_message"):
        if key in agent and isinstance(agent[key], str):
            agent[key] = _interpolate(agent[key], variables)

    return agent


def _prepare_agent_from_request(req: "MakeCallRequest") -> dict:
    """Centralised pipeline applying brand merge + all per-call overrides.

    Used by both the Twilio path (/api/call) and the web path (/api/web-call)
    so they stay in sync. Historically the Twilio path dropped voice_settings
    and phone_fx overrides — see developmentplan.md §4.6.
    """
    agent = get_agent(req.scenario, req.variables, req.brand_id)

    if req.voice_id:
        agent["voice_id"] = req.voice_id
    if req.voice_settings:
        agent["voice_settings"] = req.voice_settings
    if req.system_prompt_override:
        agent["system_prompt"] = req.system_prompt_override
    if req.first_message_override:
        agent["first_message"] = req.first_message_override
    if req.phone_fx:
        agent["phone_fx"] = True
        agent["phone_fx_settings"] = req.phone_fx_settings or {}
    return agent


# ─── Models ───

class MakeCallRequest(BaseModel):
    to_number: str
    scenario: str = "debt_reminder"
    brand_id: Optional[str] = None
    voice_id: Optional[str] = None
    variables: dict = {}
    voice_settings: Optional[dict] = None
    phone_fx: bool = False
    phone_fx_settings: Optional[dict] = None
    system_prompt_override: Optional[str] = None
    first_message_override: Optional[str] = None


class OutcomeLabelRequest(BaseModel):
    outcome: str
    notes: Optional[str] = None


class TwilioStatusCallback(BaseModel):
    CallSid: str = ""
    CallStatus: str = ""


# ─── Routes ───

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text()
    return "<h1>AI Outbound Caller</h1><p>Dashboard coming soon</p>"


@app.post("/api/call")
async def initiate_call(req: MakeCallRequest):
    """Start an outbound AI phone call."""
    try:
        agent = _prepare_agent_from_request(req)
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = make_outbound_call(req.to_number, agent, brand_id=req.brand_id)
    # Cache so the Twilio WS handler can pick up the fully-prepared agent
    # (including variables, overrides, brand tone) rather than re-loading
    # the raw scenario JSON. See developmentplan.md §4.6.
    pending_agents[result["call_id"]] = agent
    return result


@app.get("/api/calls")
async def get_calls(limit: int = 50):
    """List recent calls."""
    return storage.list_calls(limit=limit)


@app.get("/api/calls/{call_id}")
async def get_call(call_id: str):
    """Get call details."""
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return call


@app.get("/api/agents")
async def get_agents():
    """List available agent scenarios."""
    return load_agents()


@app.get("/api/brands")
async def get_brands():
    """List available brand / tenant profiles."""
    return load_brands()


@app.patch("/api/calls/{call_id}/outcome")
async def set_call_outcome(call_id: str, req: OutcomeLabelRequest):
    """Human-override the outcome label on a call.

    The QA engine writes outcome_source='qa_engine' automatically; this
    endpoint lets a reviewer correct it (source becomes 'human'). Used by
    the reviewer button in qa.html per developmentplan.md §4.7.
    """
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    allowed = {
        "converted", "qualified", "declined", "callback",
        "voicemail", "wrong_number", "other",
    }
    if req.outcome not in allowed:
        raise HTTPException(
            400,
            f"outcome must be one of: {sorted(allowed)}",
        )
    storage.set_labels(
        call_id,
        outcome=req.outcome,
        outcome_source="human",
    )
    return {
        "ok": True,
        "call_id": call_id,
        "outcome": req.outcome,
        "outcome_source": "human",
    }


@app.get("/api/voices")
async def get_voices():
    """List available ElevenLabs voices."""
    try:
        voices = await list_voices()
        return voices
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch voices: {e}")


@app.post("/api/twilio/status/{call_id}")
async def twilio_status_callback(call_id: str, request: Request):
    """Receive Twilio call status updates."""
    form = await request.form()
    status = form.get("CallStatus", "")
    print(f"[TWILIO] Call {call_id} status: {status}")
    
    if status in ("completed", "failed", "busy", "no-answer", "canceled"):
        storage.update_call(call_id, status=status)
        # Clean up session
        if call_id in active_sessions:
            await active_sessions[call_id].stop()
            del active_sessions[call_id]
    elif status == "in-progress":
        storage.update_call(call_id, status="connected")
    else:
        storage.update_call(call_id, status=status)
    
    return JSONResponse({"ok": True})


# ─── Twilio WebSocket ───

@app.websocket("/ws/twilio/{call_id}")
async def twilio_websocket(websocket: WebSocket, call_id: str):
    """Handle Twilio media stream WebSocket connection."""
    await websocket.accept()
    print(f"[WS] Twilio connected for call {call_id}")
    
    # Get call record to find agent config
    call = storage.get_call(call_id)
    if not call:
        print(f"[WS] Unknown call_id: {call_id}")
        await websocket.close()
        return
    
    # Prefer the cached, fully-prepared agent (with vars interpolated, brand
    # tone merged, overrides applied) left here by /api/call. Falls back to
    # a fresh scenario load only when the cache has expired or when Twilio
    # reconnects after a restart.
    agent = pending_agents.pop(call_id, None)
    if agent is None:
        try:
            agent = get_agent(
                call["agent_scenario"],
                brand_id=call.get("brand_id"),
            )
            if call.get("voice_id"):
                agent["voice_id"] = call["voice_id"]
        except ValueError:
            agent = get_agent("debt_reminder")
    
    # Create call session
    session = CallSession(call_id, websocket, agent)
    active_sessions[call_id] = session
    
    try:
        await session.start()
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await session.handle_twilio_message(message)
            
    except WebSocketDisconnect:
        print(f"[WS] Twilio disconnected for call {call_id}")
    except Exception as e:
        print(f"[WS] Error for call {call_id}: {e}")
    finally:
        await session.stop()
        if call_id in active_sessions:
            del active_sessions[call_id]


# ─── Web Call (browser voice test) ───

@app.get("/test", response_class=HTMLResponse)
async def web_call_page():
    page = STATIC_DIR / "web_call.html"
    if page.exists():
        return page.read_text()
    return "<h1>Web call test page not found</h1>"


@app.websocket("/ws/web/{call_id}")
async def web_call_websocket(websocket: WebSocket, call_id: str):
    """Browser-based voice call WebSocket."""
    await websocket.accept()
    print(f"[WS-WEB] Connected for call {call_id}")

    call = storage.get_call(call_id)
    if not call:
        await websocket.close()
        return

    # Use prepared agent from /api/web-call (has variables filled in)
    agent = pending_agents.pop(call_id, None)
    if not agent:
        try:
            agent = get_agent(call["agent_scenario"])
            if call.get("voice_id"):
                agent["voice_id"] = call["voice_id"]
        except ValueError:
            agent = get_agent("debt_reminder")

    session = WebCallSession(call_id, websocket, agent)
    active_sessions[call_id] = session

    try:
        await session.start()
        print(f"[WS-WEB] Session started for {call_id}", flush=True)
        while True:
            msg = await websocket.receive()
            if "bytes" in msg:
                await session.handle_audio(msg["bytes"])
            elif "text" in msg:
                data = json.loads(msg["text"])
                if data.get("type") == "stop":
                    break
    except WebSocketDisconnect:
        print(f"[WS-WEB] Disconnected {call_id}", flush=True)
    except Exception as e:
        print(f"[WS-WEB] Error {call_id}: {e}", flush=True)
        import traceback; traceback.print_exc()
    finally:
        await session.stop()
        if call_id in active_sessions:
            del active_sessions[call_id]


@app.post("/api/web-call")
async def create_web_call(req: MakeCallRequest):
    """Create a web-based test call (no Twilio, no cost)."""
    try:
        agent = _prepare_agent_from_request(req)
    except ValueError as e:
        raise HTTPException(400, str(e))

    call_id = f"web_{uuid.uuid4().hex[:12]}"
    storage.create_call(
        call_id=call_id,
        to_number="browser",
        from_number="web",
        agent_name=agent.get("name", "AI Agent"),
        agent_scenario=agent.get("scenario", "custom"),
        voice_id=agent.get("voice_id", ""),
        brand_id=req.brand_id,
        channel="voice",
        language=agent.get("language", "en"),
    )
    pending_agents[call_id] = agent  # Cache prepared agent for WS handler
    return {"call_id": call_id, "status": "ready", "ws_url": f"/ws/web/{call_id}"}


# ─── Copilot (live assist UI) ───

@app.get("/copilot", response_class=HTMLResponse)
async def copilot_page():
    page = STATIC_DIR / "copilot.html"
    return page.read_text() if page.exists() else "<h1>Copilot UI not found</h1>"


@app.websocket("/ws/copilot/{call_id}")
async def copilot_stream(websocket: WebSocket, call_id: str):
    """Stream Copilot events (transcript, coaching cards, compliance) to a
    browser UI. The bus is populated by the CallSession/WebCallSession running
    the actual call. Subscribers receive event history on connect for late-join.
    """
    await websocket.accept()
    bus = copilot_mod.get_or_create_bus(call_id)
    queue = bus.subscribe()
    print(f"[WS-COPILOT] Subscribed to call {call_id}")

    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        print(f"[WS-COPILOT] Disconnected from call {call_id}")
    except Exception as e:
        print(f"[WS-COPILOT] Error: {e}")
    finally:
        bus.unsubscribe(queue)


# ─── QA (scorecard UI + API) ───

@app.get("/qa", response_class=HTMLResponse)
async def qa_page():
    page = STATIC_DIR / "qa.html"
    return page.read_text() if page.exists() else "<h1>QA UI not found</h1>"


@app.get("/api/qa/fleet")
async def qa_fleet(limit: int = 200):
    """Return aggregated fleet stats + recent scored calls for the dashboard.
    Reads scorecards from the `summary` column — they're precomputed by
    synth_data.py or by live Copilot.finalize(). No LLM calls at request time.
    """
    calls = storage.list_calls(limit=limit)
    scorecards = []
    for c in calls:
        summary = c.get("summary")
        if not summary:
            continue
        try:
            sc = json.loads(summary)
            sc["call_id"] = c["id"]
            scorecards.append(sc)
        except (json.JSONDecodeError, TypeError):
            continue

    stats = fleet_summary(scorecards)
    return {"stats": stats, "scorecards": scorecards}


@app.get("/api/qa/{call_id}")
async def qa_for_call(call_id: str):
    """Generate or return scorecard for a single call.
    If already scored, returns cached. Otherwise runs the QA engine.
    """
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")

    # Return cached scorecard if present
    if call.get("summary"):
        try:
            return json.loads(call["summary"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Score on-demand. Pick compliance pack from the agent config.
    compliance_pack = None
    try:
        agent = get_agent(call["agent_scenario"])
        compliance_pack = agent.get("compliance_pack")
    except ValueError:
        pass

    engine = get_qa_engine()
    scorecard = await engine.score_call(call_id, compliance_pack_id=compliance_pack)
    return scorecard.to_dict()


# ─── Demo launcher ───

@app.get("/demo", response_class=HTMLResponse)
async def demo_launcher():
    """Convenience page that creates a new web call with the UTS Bahasa agent,
    opens the caller UI and the Copilot UI side-by-side, and shows the full
    scripted flow. Used as the entry point in the April demo.
    """
    page = STATIC_DIR / "demo.html"
    if page.exists():
        return page.read_text()
    return "<h1>Demo page not found</h1><p>Expected at static/demo.html</p>"


# ─── Health ───

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "active_calls": len(active_sessions),
        "twilio": bool(config.TWILIO_ACCOUNT_SID),
        "deepgram": bool(config.DEEPGRAM_API_KEY),
        "elevenlabs": bool(config.ELEVENLABS_API_KEY),
        "openai": bool(config.OPENAI_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
