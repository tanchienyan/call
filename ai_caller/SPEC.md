# AI Outbound Caller - Build Spec

## Architecture
```
Twilio (phone) ←WebSocket→ FastAPI Server ←→ Deepgram STT (realtime)
                                           ←→ GPT-4o (streaming)
                                           ←→ ElevenLabs TTS (streaming)
```

## Core Pipeline (`pipeline.py`)
- FastAPI app with WebSocket endpoint for Twilio media streams
- Each call = one `CallSession` object managing the full pipeline
- Audio flow: Twilio μ-law 8kHz → Deepgram STT → LLM → ElevenLabs TTS → back to Twilio

### CallSession
- Manages one active phone call
- Holds: Deepgram WS connection, conversation history, call metadata
- Streams Twilio audio → Deepgram
- On transcript final → send to LLM
- LLM streams text → ElevenLabs streaming TTS
- TTS audio chunks → convert to μ-law → send back to Twilio WS

### Barge-in / Interruption
- When Deepgram detects speech while TTS is playing → immediately stop TTS
- Send Twilio `clear` message to flush audio buffer
- Cancel current LLM generation

### Silence Detection
- Deepgram `endpointing` handles this (configurable ms)
- When user stops talking → Deepgram sends final transcript → triggers LLM

## Outbound Calling (`caller.py`)
- `make_call(to_number, agent_config)` → uses Twilio REST API to initiate call
- Twilio connects to our WebSocket endpoint on answer
- Agent config: system prompt, voice_id, first_message, scenario

## Agent Configs (`agents/`)
- YAML/JSON configs for different scenarios
- Each has: name, system_prompt, first_message, voice_id, language
- Pre-built scenarios: debt_reminder, appointment_confirm, satisfaction_survey, membership_renewal

## Voice Selection
- Use ElevenLabs API to list available voices
- Support voice_id in agent config
- Default: use a natural-sounding voice (not robotic)

## Recording & Transcript (`storage.py`)
- Save full conversation transcript (who said what, timestamps)
- Save call metadata (duration, cost, status)
- SQLite database for simplicity
- Optional: save audio recording

## Web Dashboard (`dashboard.py`)
- Simple FastAPI + HTML page
- List calls with status, duration, transcript
- "New Call" button: enter number + select agent/scenario
- Live call status indicator
- Play recording if available

## API Endpoints
- `POST /api/call` - initiate outbound call
- `GET /api/calls` - list calls
- `GET /api/calls/{id}` - get call detail + transcript
- `GET /api/voices` - list available ElevenLabs voices
- `GET /api/agents` - list agent configs
- `POST /api/agents` - create new agent config
- `WebSocket /ws/twilio/{call_id}` - Twilio media stream endpoint

## Tech Stack
- Python 3.11+
- FastAPI + uvicorn
- twilio SDK
- deepgram-sdk (v3+)
- elevenlabs SDK
- openai SDK
- SQLite
- audioop/pydub for audio conversion

## ENV vars needed
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE_NUMBER
- DEEPGRAM_API_KEY
- ELEVENLABS_API_KEY
- OPENAI_API_KEY
- BASE_URL (public URL for Twilio webhook, use ngrok for dev)

## File Structure
```
ai_caller/
├── main.py            # FastAPI app, routes, WebSocket handler
├── pipeline.py        # CallSession, audio pipeline logic
├── caller.py          # Outbound call initiation via Twilio
├── stt.py             # Deepgram STT wrapper
├── tts.py             # ElevenLabs TTS streaming wrapper
├── llm.py             # LLM streaming wrapper (OpenAI)
├── audio_utils.py     # μ-law conversion, audio helpers
├── storage.py         # SQLite DB, call records, transcripts
├── config.py          # Settings from env
├── agents/            # Agent scenario configs
│   ├── debt_reminder.json
│   ├── appointment_confirm.json
│   ├── satisfaction_survey.json
│   └── membership_renewal.json
├── static/
│   └── index.html     # Dashboard
├── requirements.txt
└── README.md
```
