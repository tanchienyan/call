# AI Outbound Call Center

Self-hosted AI outbound calling pipeline that sounds human. Built for TDCX demo.

**Stack:** Twilio (phone) → Deepgram STT → GPT-4o → ElevenLabs TTS

## Demo

Browser-based voice test mode — talk to the AI agent directly, no phone charges.

```
http://localhost:8000/test
```

Features:
- 4 agent scenarios (debt collection, appointment, survey, membership renewal)
- Real-time transcript display
- Voice selection with categorized dropdown (recommended / professional PVC / free)
- Phone line audio effect (bandpass filter + noise + soft clip)
- Live prompt override for testing
- Latency monitoring (LLM TTFT logged per turn)

## Architecture

```
Browser Mic (16kHz PCM)
    │
    ├──► Silero VAD (local, 10-20ms)
    ├──► Deepgram STT (streaming, Nova-3)
    │        │
    │        ▼
    │    Smart Turn v3.2 (ML-based end-of-turn detection, 12-65ms)
    │        │
    │        ▼
    │    Backchannel Filter ("mm-hm", "yeah" → ignored, don't interrupt AI)
    │        │
    │        ▼
    │    GPT-4o (streaming, temperature 1.0)
    │        │
    │        ▼
    │    Sentence Buffer (punctuation-triggered, not char-count)
    │        │
    │        ▼
    │    ElevenLabs TTS (Flash v2.5, pre-warmed HTTP/2 connection pool)
    │        │
    │        ▼
    │    Phone FX (optional bandpass + noise + soft clip)
    │        │
    │        ▼
    └──► Browser Audio (24kHz PCM, gapless scheduling)
```

For real phone calls, Twilio WebSocket replaces the browser path with μ-law 8kHz audio.

## Quick Start

### 1. Clone

```bash
git clone https://github.com/zbw790/mystery.git
cd mystery/ai_caller
```

### 2. Python Environment

Requires Python 3.10+.

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install "pipecat-ai[silero]"  # Smart Turn model
```

### 3. API Keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=sk_...
TWILIO_ACCOUNT_SID=AC...
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
TWILIO_PHONE_NUMBER=+1...
BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

**Where to get keys:**

| Service | URL | Free Tier |
|---------|-----|-----------|
| OpenAI | https://platform.openai.com/api-keys | Pay-as-you-go |
| Deepgram | https://console.deepgram.com | $200 free credit |
| ElevenLabs | https://elevenlabs.io | 10k chars/month free (limited voices) |
| Twilio | https://console.twilio.com | ~$15 trial credit |

### 4. Run

```bash
python3 main.py
```

Open `http://localhost:8000/test` in your browser. Click the mic button to start a conversation.

### 5. Real Phone Calls (Optional)

For actual outbound calls via Twilio, you need a public URL:

```bash
# Terminal 2
ngrok http 8000
```

Update `BASE_URL` in `.env` with the ngrok URL. Then use the dashboard at `http://localhost:8000` to make calls.

## Project Structure

```
ai_caller/
├── main.py              # FastAPI server, REST + WebSocket endpoints
├── web_session.py       # Browser voice call session (STT → LLM → TTS)
├── pipeline.py          # Phone call session (Twilio ↔ Deepgram ↔ GPT-4o ↔ ElevenLabs)
├── stt.py               # Deepgram real-time STT (WebSocket)
├── tts.py               # ElevenLabs streaming TTS (connection pool)
├── llm.py               # GPT-4o streaming
├── smart_turn.py        # Smart Turn v3.2 ML end-of-turn detection
├── phone_fx.py          # Phone line audio effects
├── audio_utils.py       # μ-law / PCM conversion
├── caller.py            # Twilio outbound call initiation
├── storage.py           # SQLite DB for calls + transcripts
├── config.py            # Environment config
├── agents/              # Agent scenario configs (JSON)
│   ├── debt_reminder.json
│   ├── appointment_confirm.json
│   ├── satisfaction_survey.json
│   └── membership_renewal.json
└── static/
    ├── index.html       # Dashboard
    └── web_call.html    # Browser voice test UI
```

## Agent Configuration

Each scenario in `agents/` is a JSON file:

```json
{
  "name": "Emma",
  "scenario": "debt_reminder",
  "description": "Friendly payment reminder call",
  "voice_id": "PT4nqlKZfc06VW1BuClj",
  "language": "en",
  "first_message": "Hi, is this {{customer_name}}?",
  "system_prompt": "..."
}
```

Template variables (`{{customer_name}}`, `{{amount}}`, etc.) are filled from the UI or API request.

### Adding a New Scenario

1. Create `agents/your_scenario.json` following the format above
2. Pick a voice from the ElevenLabs voice library
3. Write a system prompt (see existing ones for the prompt framework)
4. Restart the server — it auto-discovers new scenarios

## Voice Selection

Voices are categorized in the UI:

- **⭐ Recommended** — ElevenLabs official picks for conversational AI
- **🎙️ Professional (PVC)** — Real human voice clones, most realistic, requires paid tier
- **🆓 Premade** — Free tier compatible

To add a voice: find its ID on [ElevenLabs](https://elevenlabs.io/voice-library) and add it to the recommended list in `static/web_call.html`.

## Prompt Engineering

The system prompts are designed based on conversational linguistics research:

- **Pause system** — Pauses at cognitive boundaries, not mechanical intervals
- **uh/um distinction** — "uh" = short word search, "um" = longer planning pause
- **Telephone opening sequence** — Follows Schegloff's 4-step structure
- **Backchannel responses** — Always acknowledge before responding
- **Forbidden words** — No "Certainly", "Absolutely", "I'd be happy to" (AI tells)
- **Number formatting** — All numbers written as words for TTS accuracy

Use the **Prompt Override** panel in the test UI to experiment without changing backend files.

## Latency Optimizations

| Optimization | Impact |
|-------------|--------|
| TTS punctuation-triggered (not 15-char buffer) | -150~300ms |
| HTTP/2 connection pool (pre-warmed) | -300ms |
| Deepgram smart_format=false | -50ms |
| Smart Turn v3.2 (ML turn detection) | Better turn accuracy |
| Backchannel filtering | No false interruptions |
| Context truncation on barge-in | No hallucinated references |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/test` | Browser voice test UI |
| GET | `/` | Dashboard |
| GET | `/api/agents` | List available scenarios |
| GET | `/api/voices` | List ElevenLabs voices |
| GET | `/api/health` | Health check (all services) |
| POST | `/api/web-call` | Create browser test call |
| POST | `/api/call` | Make real phone call (Twilio) |
| WS | `/ws/web/{call_id}` | Browser voice WebSocket |
| WS | `/ws/{call_id}` | Twilio media WebSocket |

## Cost Estimates

Per 3-minute call:

| Component | Cost |
|-----------|------|
| Deepgram STT | ~$0.04 |
| GPT-4o | ~$0.02-0.05 |
| ElevenLabs TTS | ~$0.10-0.20 |
| Twilio (US→US) | ~$0.03 |
| **Total** | **~$0.20-0.30** |

Browser test mode: no Twilio cost, ~$0.15-0.25 per call.

Compare: TDCX human agent ~$0.89/call (Malaysia).

## Troubleshooting

**No sound in browser test:**
- Check browser console (F12) for errors
- Ensure ElevenLabs API key is valid and has credits
- Try a different voice (some require paid tier)
- Hard refresh: Cmd+Shift+R

**High latency:**
- Check `[LATENCY]` logs for LLM TTFT
- Consider switching to GPT-4o-mini in `llm.py`
- Ensure server is in same region as API providers

**STT not picking up speech:**
- Check microphone permissions in browser
- Verify Deepgram API key with `/api/health`

## License

MIT
