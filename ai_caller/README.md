# AI Outbound Caller 📞

Self-hosted AI phone calling pipeline: Twilio + Deepgram STT + GPT-4o + ElevenLabs TTS.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env

# Start the server
python main.py

# Expose to internet (Twilio needs a public URL)
ngrok http 8000

# Update BASE_URL in .env with your ngrok URL
```

## Make a Call

1. Open http://localhost:8000
2. Enter a phone number, pick a scenario and voice
3. Click "Start Call"

Or via API:
```bash
curl -X POST http://localhost:8000/api/call \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+447123456789",
    "scenario": "debt_reminder",
    "variables": {
      "customer_name": "John",
      "company_name": "Nexus Financial",
      "amount": "$245.50"
    }
  }'
```

## Architecture

```
Phone Call ←→ Twilio WebSocket ←→ FastAPI Server
                                    ├── Deepgram (real-time STT)
                                    ├── GPT-4o (conversation brain)
                                    └── ElevenLabs (streaming TTS)
```

## Scenarios

- **debt_reminder** — Friendly payment reminder (Emma)
- **appointment_confirm** — Quick appointment confirmation (Jake)  
- **satisfaction_survey** — Post-service feedback (Priya)
- **membership_renewal** — Renewal/retention call (Marcus)

## Cost per 3-min Call

| Component | Cost |
|-----------|------|
| Twilio | ~$0.04 |
| Deepgram | ~$0.013 |
| ElevenLabs | ~$0.18-0.36 |
| GPT-4o | ~$0.03-0.09 |
| **Total** | **~$0.26-0.50** |
