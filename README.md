# Rivorix

Self-hosted AI outbound voice platform — live human-in-the-loop coaching and 100% automated post-call QA for regulated telemarketing.

> **If you're here for the UTS Worldwide demo:** everything you need is in `ai_caller/` (live product) and `docs/` (strategy + demo-day materials).

## Repository layout

```
.
├── ai_caller/            # ACTIVE PRODUCT — FastAPI + Twilio + Deepgram + OpenAI + ElevenLabs
│                         # All new engineering happens here.
│
├── docs/                 # Strategy, engineering plan, demo-day deliverables
│   ├── plan.md                      # 2-week sprint plan (source of truth)
│   ├── developer_plan.md            # Engineering task breakdown (what to build)
│   ├── pivot.md                     # GTM rationale for the healthcare / BPO pivot
│   ├── architecture.md              # 1-pager (pairs with PDF for demo)
│   ├── piam_coverage.md             # 10-rule PIAM compliance pack summary (1-pager)
│   ├── pilot_scope.md               # 30-day pilot proposal (1-pager)
│   ├── ask_kenneth.md               # Three discovery questions for UTS demo
│   ├── references/                  # Patterns distilled from earlier codebases
│   └── archive/                     # Retired strategy docs
│
├── mystery_shopper/      # REFERENCE-ONLY — pre-pivot hotel mystery-shopping codebase
│                         # Do not import from ai_caller/. Archive after 90d idle.
│                         # See mystery_shopper/README.md for the scoping contract.
│
└── README.md             # This file
```

Archived pre-pivot scaffolds live in the sibling repo `../rivorix-archive/` (not part of this monorepo).

## Quick start (UTS demo)

```bash
cd ai_caller
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in OpenAI / Deepgram / ElevenLabs / Twilio keys
python scripts/demo_launch.py   # probes providers, seeds synthetic fleet, opens /demo
```

Acceptance: `http://localhost:8000/api/health` returns `{status: "ok", openai: true, deepgram: true, elevenlabs: true}`. Any `false` means the corresponding provider is down — fix before proceeding (common issues in `docs/developer_plan.md` §3).

## Where things are

| I want to… | Go to |
|---|---|
| Understand the product pitch | `docs/architecture.md` |
| Understand the compliance posture | `docs/piam_coverage.md` |
| Understand the pilot offer | `docs/pilot_scope.md` |
| Understand what the team is building this sprint | `docs/developer_plan.md` |
| Understand the strategy | `docs/plan.md` |
| Build a new agent scenario | `ai_caller/agents/*.json` |
| Build a new brand profile | `ai_caller/agents/brands/*.json` |
| Add a new compliance rule pack | `ai_caller/compliance/*.json` |
| Investigate reference patterns from earlier | `docs/references/` |

## Engineering conventions

- `ai_caller/` is the canonical product root. Dependencies, env, scripts, tests all live there.
- **Do not** add new files to the repo root. Use `ai_caller/`, `docs/`, or `mystery_shopper/`.
- **Do not** import from `mystery_shopper/` at runtime. Port distilled patterns to `docs/references/` instead.
- Commits touching both `ai_caller/` and `docs/` should be split into separate logical commits.
- `.env` files live inside `ai_caller/` only (never at root, never in `mystery_shopper/`). Template is `ai_caller/.env.example`.

## Status

| Component | Status |
|---|---|
| First-Touch AI (Bahasa outbound) | ✅ shipped, awaiting voice A/B |
| Live Copilot | ✅ shipped, compliance pack v0 (10 rules) |
| Auto-QA + fleet dashboard | ✅ shipped, synthetic fleet populated |
| Warm transfer | ⚠️ working; edge cases under test |
| Batch calling | ⏸️ deferred post-demo (per `docs/plan.md` §3.4) |
| WhatsApp / inbound | ⏸️ post-pilot |

Current sprint tracker: `docs/developer_plan.md` §4.
