"""Outbound call initiation via Twilio."""
import uuid
from twilio.rest import Client
import config
import storage


def make_outbound_call(to_number: str, agent_config: dict) -> dict:
    """Initiate an outbound phone call via Twilio.
    
    Twilio will connect to our WebSocket when the call is answered.
    Returns call info dict.
    """
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    
    # Create call record in DB
    storage.create_call(
        call_id=call_id,
        to_number=to_number,
        from_number=config.TWILIO_PHONE_NUMBER,
        agent_name=agent_config.get("name", "AI Agent"),
        agent_scenario=agent_config.get("scenario", "custom"),
        voice_id=agent_config.get("voice_id", ""),
    )
    
    # Build TwiML that connects to our WebSocket
    base_url = config.BASE_URL
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}/ws/twilio/{call_id}">
            <Parameter name="call_id" value="{call_id}" />
        </Stream>
    </Connect>
</Response>"""
    
    # Make the call via Twilio
    # Use API Key auth if available, otherwise Account SID + Auth Token
    if config.TWILIO_API_KEY_SID:
        client = Client(config.TWILIO_API_KEY_SID, config.TWILIO_API_KEY_SECRET,
                        config.TWILIO_ACCOUNT_SID)
    else:
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    
    call = client.calls.create(
        to=to_number,
        from_=config.TWILIO_PHONE_NUMBER,
        twiml=twiml,
        status_callback=f"{base_url}/api/twilio/status/{call_id}",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        status_callback_method="POST",
    )
    
    # Update with Twilio SID
    storage.update_call(call_id, twilio_call_sid=call.sid, status="ringing")
    
    return {
        "call_id": call_id,
        "twilio_sid": call.sid,
        "status": "ringing",
        "to": to_number,
        "from": config.TWILIO_PHONE_NUMBER,
    }
