"""AI Outbound Caller — FastAPI server with Twilio WebSocket integration."""
import json
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

app = FastAPI(title="AI Outbound Caller", version="1.0")

# Active call sessions
active_sessions: dict[str, CallSession] = {}
pending_agents: dict[str, dict] = {}  # call_id → prepared agent config

# Static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Agent configs
AGENTS_DIR = Path(__file__).parent / "agents"
_agents_cache = {}


def load_agents() -> dict:
    """Load all agent scenario configs."""
    agents = {}
    for f in AGENTS_DIR.glob("*.json"):
        with open(f) as fh:
            data = json.load(fh)
            agents[data["scenario"]] = data
    return agents


def get_agent(scenario: str, variables: dict = None) -> dict:
    """Get agent config with template variables filled in."""
    agents = load_agents()
    if scenario not in agents:
        raise ValueError(f"Unknown scenario: {scenario}")
    
    agent = agents[scenario].copy()
    variables = variables or {}
    
    # Replace template variables in prompts
    for key in ["system_prompt", "first_message"]:
        if key in agent:
            for var, val in variables.items():
                agent[key] = agent[key].replace("{{" + var + "}}", val)
            # Remove unfilled placeholders
            import re
            agent[key] = re.sub(r'\{\{[^}]+\}\}', '[not specified]', agent[key])
    
    return agent


# ─── Models ───

class MakeCallRequest(BaseModel):
    to_number: str
    scenario: str = "debt_reminder"
    voice_id: Optional[str] = None
    variables: dict = {}
    voice_settings: Optional[dict] = None
    phone_fx: bool = False
    phone_fx_settings: Optional[dict] = None
    system_prompt_override: Optional[str] = None
    first_message_override: Optional[str] = None


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
        agent = get_agent(req.scenario, req.variables)
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    # Override voice if specified
    if req.voice_id:
        agent["voice_id"] = req.voice_id
    
    result = make_outbound_call(req.to_number, agent)
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
    
    # Load agent config
    try:
        agent = get_agent(call["agent_scenario"])
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
        agent = get_agent(req.scenario, req.variables)
    except ValueError as e:
        raise HTTPException(400, str(e))

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

    call_id = f"web_{uuid.uuid4().hex[:12]}"
    storage.create_call(
        call_id=call_id,
        to_number="browser",
        from_number="web",
        agent_name=agent.get("name", "AI Agent"),
        agent_scenario=agent.get("scenario", "custom"),
        voice_id=agent.get("voice_id", ""),
    )
    pending_agents[call_id] = agent  # Cache prepared agent for WS handler
    return {"call_id": call_id, "status": "ready", "ws_url": f"/ws/web/{call_id}"}


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
