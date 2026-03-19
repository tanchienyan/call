"""Mystery Shopper Platform — FastAPI backend."""

import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional

from . import database as db
from .channels import phone, email_channel, webchat, scoring
from .config import settings

app = FastAPI(title="Mystery Shopper", version="2.0")

# Serve static frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Serve screenshots
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")


# ─── Models ───

class CreateMission(BaseModel):
    hotel_name: str
    hotel_website: str = ""
    hotel_email: str = ""
    hotel_phone: str = ""
    hotel_whatsapp: str = ""
    persona_name: str = "Sarah Mitchell"
    channels: list[str] = ["phone"]  # phone, email, webchat, browse, whatsapp


class PhoneCallRequest(BaseModel):
    to_number: str
    mission_id: Optional[str] = None


class EmailRequest(BaseModel):
    to_email: str
    hotel_name: str = ""
    mission_id: Optional[str] = None


class WebchatRequest(BaseModel):
    url: str
    message: str = "Hi, I'm looking to book a room for next Thursday to Sunday. Do you have availability?"
    mission_id: Optional[str] = None


class ScoreRequest(BaseModel):
    mission_id: str


# ─── Dashboard ───

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text()
    return "<h1>Mystery Shopper</h1><p>Build the frontend at app/static/index.html</p>"


# ─── Missions API ───

@app.post("/api/missions")
async def create_mission(req: CreateMission, background_tasks: BackgroundTasks):
    mission_id = f"ms_{uuid.uuid4().hex[:12]}"
    mission = db.create_mission(
        mission_id=mission_id,
        hotel_name=req.hotel_name,
        hotel_website=req.hotel_website,
        hotel_email=req.hotel_email,
        hotel_phone=req.hotel_phone,
        hotel_whatsapp=req.hotel_whatsapp,
        persona_name=req.persona_name,
    )

    # Create steps based on requested channels
    step_order = 0

    if "browse" in req.channels and req.hotel_website:
        step_order += 1
        db.create_step(mission_id, step_order, "browse_website", "Browse Hotel Website",
                       {"url": req.hotel_website})

    if "webchat" in req.channels and req.hotel_website:
        step_order += 1
        db.create_step(mission_id, step_order, "webchat", "Webchat Inquiry",
                       {"url": req.hotel_website})

    if "email" in req.channels and req.hotel_email:
        step_order += 1
        db.create_step(mission_id, step_order, "send_email", "Email Inquiry",
                       {"to": req.hotel_email})

    if "phone" in req.channels and req.hotel_phone:
        step_order += 1
        db.create_step(mission_id, step_order, "phone_call", "Phone Call",
                       {"phone_number": req.hotel_phone})

    # Start execution in background
    background_tasks.add_task(execute_mission, mission_id)

    return {"mission_id": mission_id, "status": "created", "steps": step_order}


@app.get("/api/missions")
async def get_missions(limit: int = 50):
    missions = db.list_missions(limit=limit)
    for m in missions:
        m["steps"] = db.get_steps(m["id"])
    return missions


@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    mission = db.get_mission(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    mission["steps"] = db.get_steps(mission_id)
    mission["calls"] = db.get_call_records(mission_id)
    if mission.get("analysis_json"):
        mission["analysis"] = json.loads(mission["analysis_json"])
    return mission


@app.delete("/api/missions/{mission_id}")
async def delete_mission(mission_id: str):
    conn = db.get_db()
    conn.execute("DELETE FROM steps WHERE mission_id=?", (mission_id,))
    conn.execute("DELETE FROM call_records WHERE mission_id=?", (mission_id,))
    conn.execute("DELETE FROM missions WHERE id=?", (mission_id,))
    conn.commit()
    conn.close()
    return {"deleted": True}


# ─── Individual Channel Endpoints ───

@app.post("/api/call")
async def make_phone_call(req: PhoneCallRequest, background_tasks: BackgroundTasks):
    """Initiate a mystery shopping phone call."""
    mission_id = req.mission_id or f"quick_{uuid.uuid4().hex[:8]}"

    # Create mission if needed
    if not db.get_mission(mission_id):
        db.create_mission(mission_id, hotel_name=f"Quick call to {req.to_number}",
                          hotel_phone=req.to_number)

    step_id = db.create_step(mission_id, 1, "phone_call", "Phone Call",
                             {"phone_number": req.to_number})
    db.update_step(step_id, status="running", started_at=datetime.utcnow().isoformat())

    # Make the call (async in background)
    background_tasks.add_task(_run_phone_call, mission_id, step_id, req.to_number)

    return {"mission_id": mission_id, "step_id": step_id, "status": "calling"}


@app.post("/api/email")
async def send_email(req: EmailRequest, background_tasks: BackgroundTasks):
    """Send a mystery shopping inquiry email."""
    result = await email_channel.send_inquiry(
        to_email=req.to_email,
        hotel_name=req.hotel_name,
    )

    mission_id = req.mission_id or f"quick_{uuid.uuid4().hex[:8]}"
    if not db.get_mission(mission_id):
        db.create_mission(mission_id, hotel_name=req.hotel_name or f"Email to {req.to_email}",
                          hotel_email=req.to_email)

    step_id = db.create_step(mission_id, 1, "send_email", "Email Inquiry",
                             {"to": req.to_email})
    db.update_step(step_id,
                   status="completed" if result["sent"] else "failed",
                   data_sent=result.get("body", ""),
                   notes=result.get("error", f"Sent to {req.to_email}"),
                   started_at=datetime.utcnow().isoformat(),
                   completed_at=datetime.utcnow().isoformat())

    return {"mission_id": mission_id, "step_id": step_id, **result}


@app.post("/api/webchat")
async def test_webchat(req: WebchatRequest):
    """Test a hotel's webchat widget."""
    detection = await webchat.detect_chat_widget(req.url)
    result = {"detection": detection}

    if detection.get("has_chat"):
        interaction = await webchat.chat_interaction(req.url, [req.message])
        result["interaction"] = interaction

    return result


@app.post("/api/browse")
async def browse_hotel(req: WebchatRequest):
    """Browse a hotel website and extract information."""
    result = await webchat.browse_website(req.url)
    return result


# ─── Call Status Polling ───

@app.get("/api/calls/{call_id}")
async def get_call(call_id: str):
    """Get status/details of a specific Retell call."""
    return await phone.get_call_status(call_id)


@app.get("/api/calls")
async def list_recent_calls(limit: int = 20):
    """List recent Retell calls."""
    return await phone.list_calls(limit=limit)


# ─── Scoring ───

@app.post("/api/score/call")
async def score_call(mission_id: str):
    """Score a phone call from a mission."""
    calls = db.get_call_records(mission_id)
    if not calls:
        raise HTTPException(404, "No call records found")

    call = calls[-1]  # Latest call
    transcript = call.get("transcript", "")
    if not transcript:
        raise HTTPException(400, "No transcript available")

    mission = db.get_mission(mission_id)
    scores = scoring.score_phone_call(transcript, mission.get("hotel_name", ""))
    return scores


@app.post("/api/score/mission/{mission_id}")
async def score_mission(mission_id: str):
    """Run full journey scoring for a mission."""
    mission = db.get_mission(mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")

    steps = db.get_steps(mission_id)
    analysis = scoring.score_full_journey(steps, mission.get("hotel_name", ""))

    db.update_mission(mission_id,
                      overall_score=analysis.get("overall_score"),
                      analysis_json=json.dumps(analysis, ensure_ascii=False))

    return analysis


# ─── Background task runners ───

async def _run_phone_call(mission_id: str, step_id: int, to_number: str):
    """Background: make call, poll for result, score, save."""
    try:
        result = await phone.make_call(to_number)

        db.update_step(step_id,
                       status="completed" if result.get("status") == "ended" else "failed",
                       transcript=result.get("transcript", ""),
                       recording_url=result.get("recording_url", ""),
                       data_received=result.get("transcript", ""),
                       response_time_seconds=result.get("duration_seconds", 0),
                       notes=result.get("analysis", {}).get("summary", ""),
                       completed_at=datetime.utcnow().isoformat())

        # Save call record
        db.save_call_record(
            mission_id=mission_id,
            step_id=step_id,
            retell_call_id=result.get("call_id", ""),
            call_type="phone_call",
            from_number=phone.FROM_NUMBER,
            to_number=to_number,
            duration_seconds=result.get("duration_seconds", 0),
            transcript=result.get("transcript", ""),
            recording_url=result.get("recording_url", ""),
            cost_cents=result.get("cost_cents", 0),
            analysis=result.get("analysis", {}),
        )

        # Auto-score if transcript available
        transcript = result.get("transcript", "")
        if transcript and settings.OPENAI_API_KEY:
            mission = db.get_mission(mission_id)
            scores = scoring.score_phone_call(transcript, mission.get("hotel_name", ""))
            db.update_step(step_id, score=scores.get("overall_score"),
                           sentiment_json=json.dumps(scores, ensure_ascii=False))
            db.update_mission(mission_id,
                              overall_score=scores.get("overall_score"),
                              analysis_json=json.dumps(scores, ensure_ascii=False),
                              status="completed",
                              completed_at=datetime.utcnow().isoformat())
        else:
            db.update_mission(mission_id, status="completed",
                              completed_at=datetime.utcnow().isoformat())

    except Exception as e:
        db.update_step(step_id, status="failed", notes=str(e),
                       completed_at=datetime.utcnow().isoformat())
        db.update_mission(mission_id, status="failed",
                          completed_at=datetime.utcnow().isoformat())


async def execute_mission(mission_id: str):
    """Execute all steps of a mission sequentially."""
    db.update_mission(mission_id, status="running",
                      started_at=datetime.utcnow().isoformat())
    steps = db.get_steps(mission_id)
    mission = db.get_mission(mission_id)

    for step in steps:
        step_id = step["id"]
        step_type = step["step_type"]
        config = json.loads(step.get("config_json", "{}"))

        db.update_step(step_id, status="running",
                       started_at=datetime.utcnow().isoformat())

        try:
            if step_type == "browse_website":
                url = config.get("url", mission.get("hotel_website", ""))
                result = await webchat.browse_website(url)
                db.update_step(step_id,
                               status="completed",
                               notes=f"Title: {result.get('title', '')}. Chat: {'Yes' if result.get('has_chat') else 'No'}. Booking: {'Yes' if result.get('has_booking') else 'No'}.",
                               screenshots_json=result.get("screenshots", []),
                               completed_at=datetime.utcnow().isoformat())

            elif step_type == "webchat":
                url = config.get("url", mission.get("hotel_website", ""))
                detection = await webchat.detect_chat_widget(url)
                if detection.get("has_chat"):
                    interaction = await webchat.chat_interaction(url)
                    db.update_step(step_id,
                                   status="completed" if interaction.get("success") else "failed",
                                   data_sent="\n".join(interaction.get("messages_sent", [])),
                                   data_received=interaction.get("transcript", ""),
                                   notes=f"Provider: {detection.get('provider', 'Unknown')}",
                                   screenshots_json=interaction.get("screenshots", []),
                                   completed_at=datetime.utcnow().isoformat())
                else:
                    db.update_step(step_id,
                                   status="skipped",
                                   notes="No chat widget detected",
                                   completed_at=datetime.utcnow().isoformat())

            elif step_type == "send_email":
                to = config.get("to", mission.get("hotel_email", ""))
                result = await email_channel.send_inquiry(to_email=to, hotel_name=mission.get("hotel_name", ""))
                db.update_step(step_id,
                               status="completed" if result["sent"] else "failed",
                               data_sent=result.get("body", ""),
                               notes=f"Sent to {to}" if result["sent"] else result.get("error", ""),
                               completed_at=datetime.utcnow().isoformat())

            elif step_type == "phone_call":
                number = config.get("phone_number", mission.get("hotel_phone", ""))
                await _run_phone_call(mission_id, step_id, number)

            else:
                db.update_step(step_id, status="skipped",
                               notes=f"Handler not implemented for {step_type}",
                               completed_at=datetime.utcnow().isoformat())

        except Exception as e:
            db.update_step(step_id, status="failed", notes=str(e),
                           completed_at=datetime.utcnow().isoformat())

    # Final scoring
    try:
        steps = db.get_steps(mission_id)
        if settings.OPENAI_API_KEY:
            analysis = scoring.score_full_journey(steps, mission.get("hotel_name", ""))
            db.update_mission(mission_id,
                              overall_score=analysis.get("overall_score"),
                              analysis_json=json.dumps(analysis, ensure_ascii=False),
                              status="completed",
                              completed_at=datetime.utcnow().isoformat())
        else:
            db.update_mission(mission_id, status="completed",
                              completed_at=datetime.utcnow().isoformat())
    except Exception as e:
        db.update_mission(mission_id, status="completed",
                          completed_at=datetime.utcnow().isoformat())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
