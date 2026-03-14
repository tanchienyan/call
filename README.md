# AI Mystery Shopper 🕵️

AI-powered omnichannel mystery shopping platform for hotels and service businesses.

## What it does

Automatically tests your business's customer service quality across multiple channels:

- 📧 **Email** — Sends inquiry emails, measures response time, scores quality
- 📞 **Phone** — AI voice agent calls your front desk, evaluates the conversation
- 💬 **Webchat** — Tests live chat response (coming soon)

Generates a comprehensive scorecard showing exactly where your team excels and where they need improvement.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the demo
python -m mystery_shopper.cli demo --target "Hotel Name" --email front@hotel.com --phone +44123456789

# Start the web dashboard
python -m mystery_shopper.web
```

## Architecture

```
mystery_shopper/
├── channels/          # Channel implementations
│   ├── email.py       # Email mystery shopping
│   ├── phone.py       # AI voice call mystery shopping
│   └── webchat.py     # Webchat testing
├── scoring/           # Scoring engine
│   ├── engine.py      # LLM-based scoring
│   └── criteria.py    # Industry-specific scoring criteria
├── scenarios/         # Test scenarios (personas, scripts)
│   └── hotel.py       # Hotel-specific scenarios
├── reporting/         # Report generation
│   └── report.py      # Scorecard generation
├── web.py             # Web dashboard
└── cli.py             # CLI interface
```

## Tech Stack

- **Voice AI**: Retell AI / Vapi (for phone calls)
- **LLM**: OpenAI GPT-4 / Anthropic Claude (for scoring & conversation)
- **Email**: SMTP / Gmail API
- **Web**: FastAPI + simple HTML dashboard
