# mystery_shopper → ai_caller — Distilled Patterns

**Source:** `mystery_shopper/` (reference-only, see `docs/plan.md` §3.2).
**Purpose:** document what `ai_caller/` inherited from the Hilton-demo codebase, and what to reach for if we ever need to re-extend. Runtime imports from `mystery_shopper/` are forbidden — this file is the contract.

Last distilled: 2026-04-21.

---

## 1. LLM scoring with weighted criteria (`list[dict]`, not `dict[str, Criterion]`)

**Where it lives:** `mystery_shopper/scoring/engine.py`, the `criteria: list[dict]` parameter.

**Why list-of-dicts, not a typed schema:**

- Criteria are authored by non-engineers (compliance, ops). List-of-dicts in JSON is editable without touching Python.
- Weight is explicit and summable (`sum(c["weight"] for c in criteria)` catches drift, §plan-safe).
- Rubric is a `dict[str, str]` mapping score range to description — renders directly into the LLM prompt.

**Minimum viable criterion:**

```python
{
    "id": "answer_speed",
    "name": "Answer Speed",
    "description": "How quickly was the phone answered?",
    "weight": 10,                      # % of total; all criteria sum to 100
    "rubric": {
        "90-100": "Answered within 3 rings",
        "70-89":  "Answered within 5 rings",
        "50-69":  "Answered within 8 rings",
        "30-49":  "Answered after long wait",
        "0-29":   "Not answered / voicemail",
    },
}
```

**LLM prompt shape** (reference-preserved):

```
## Scoring Criteria
### <name> (weight: <weight>%)
<description>
Scoring rubric:
  - 90-100: <desc>
  - 70-89:  <desc>
  ...
```

**What `ai_caller/qa_engine.py` does with this:** same schema, different lifecycle — scored post-call from transcript + labels rather than from synthetic outbound/inbound pairs. The `ScoreItem` dict shape (`{criterion_id, criterion_name, score, notes}`) is preserved verbatim so downstream analytics code doesn't have to branch.

---

## 2. Persona-based scenario config

**Where it lives:** `mystery_shopper/scenarios/hotel.py`, the `PERSONAS` list.

**Pattern:** a scenario is the pair (personas, scoring criteria). Personas drive outbound generation; criteria drive inbound scoring. Both are pure data.

**Persona shape:**

```python
{
    "name": "Sarah Mitchell",
    "background": "Business traveler, mid-30s, traveling for a conference",
    "style": "Professional, polite but time-pressed",
    "needs": {
        "dates": "next Thursday to Sunday (3 nights)",
        "guests": "1 adult",
        "room_type": "quiet room, preferably high floor",
        "budget": "doesn't mention budget unless asked",
        "extras": "interested in late checkout, wants to know about gym/wifi",
    },
}
```

**Why this is useful for Bloom / UTS pivots:**

- Bloom: personas become patient archetypes (annual-checkup adult, post-op follow-up, missed-appointment). `needs` become medical history / preferred provider / language preference.
- UTS: personas are cardholder archetypes (high balance, dormant, existing transfer-plan holder). `needs` are objection set + willingness to transfer.

The mistake is putting persona data inside the system prompt. Keep it separate, interpolate at call time — `ai_caller/main.py:_prepare_agent_from_request` does exactly this with brand `default_variables` merged into per-call `variables`.

---

## 3. Channel abstraction

**Where it lives:** `mystery_shopper/channels/{phone,phone_retell,whatsapp,web_browser}.py`.

**Pattern:** each channel module exports one coroutine with the signature:

```python
async def <channel>_<verb>(step: JourneyStep, context: dict) -> StepResult
```

…and the orchestrator invokes them without knowing the channel. New channels are added by dropping a file in the directory.

**Why `ai_caller/` didn't copy this verbatim:** we collapsed phone+browser into a single pipeline (`ai_caller/pipeline.py` + `web_session.py`) because the STT/TTS/LLM stack is channel-agnostic. The split was re-emerging as WhatsApp and inbound get added (see `.cursor` workspace rule, always-applied — patient recall is multi-channel). When that happens, resurrect this abstraction at the `ai_caller/channels/` level rather than forking `web_session.py`.

**Retell SDK note (`phone_retell.py`):** do not reintroduce Retell into `ai_caller/`. The self-hosted Twilio + Deepgram + OpenAI + ElevenLabs pipeline is deliberate — Retell was a bootstrap, not a platform decision. See git history rotate-away commit.

---

## 4. Retell agent prompt structure → `ai_caller/agents/*.json`

**What transferred:**

- **Opening sequence as numbered steps.** Retell prompts split "1. Greet and confirm identity → 2. Self-introduce → 3. State reason" into enumerated steps. This lives verbatim in `agents/uts_bt_en.json` and `uts_bt_bahasa.json`.
- **Hard boundaries section.** What the agent *cannot* do (close, quote effective rate, use pressure). Retell prompts called this "constraints"; we renamed to "HARD BOUNDARIES" for emphasis.
- **Explicit `# NUMBERS` block.** "three point five percent" not "3.5%" — originally a Retell SOP for avoiding TTS mispronunciation.
- **`# ONE QUESTION AT A TIME` cadence rule.** Retell called this "turn discipline."

**What we added post-pivot:**

- Proactive AI-identity disclosure as a compliance requirement in the first two turns.
- Brand tone prepended by `_prepare_agent_from_request` (multi-tenancy).
- Warm-transfer marker (`[TRANSFER_TO_HUMAN]`) that triggers AI silence (`web_session.transferred` flag).

---

## 5. Orchestrator pattern — what we *didn't* port

`mystery_shopper/orchestrator/{real_journey,demo_journey,journey}.py` implements a DAG executor for multi-step mystery-shopping journeys (call hotel → WhatsApp follow-up → score both).

`ai_caller/` deliberately doesn't have this because our product is single-call-at-a-time. If batch calling (`plan.md` §3.4 deferred) becomes a pilot requirement, don't fork the orchestrator — rebuild it around `asyncio.gather` with a concurrency limit and a Redis/SQLite job queue. The journey semantics in `mystery_shopper` are tangled with pre-LLM-first-class patterns.

---

## 6. Reporting (`mystery_shopper/reporting/report.py`)

Markdown-first report generator — scorecard → markdown → PDF via pandoc. `ai_caller/qa_engine.py` persists structured labels instead and renders via `static/qa.html`. **Don't port the MD-based report path back in** — the structured-label + JSON path is queryable and the UI is already there.

If we need exportable PDF reports for UTS (post-demo), add a `qa_engine.export_pdf(call_id)` method that renders the existing scorecard JSON through a pandoc template. Don't resurrect the markdown-generation flow.

---

## 7. Sentiment analysis (`mystery_shopper/analytics/*`)

Not ported. `ai_caller/qa_engine.py` folds sentiment into the LLM scorecard directly ("tone" criterion). If customer-side real-time sentiment becomes a Copilot feature, port `analytics/sentiment.py` as a new `ai_caller/copilot_sentiment.py` that subscribes to the CopilotBus — don't import from `mystery_shopper/`.

---

## When NOT to reach into `mystery_shopper/`

- You want to add a new scenario → use `ai_caller/agents/*.json` + `coaching/*.json`.
- You want to add a new brand → use `ai_caller/agents/brands/*.json`.
- You want to add a compliance rule → use `ai_caller/compliance/*.json` + the existing engine.
- You want to add batch calling → build fresh in `ai_caller/`; see above.
- You want to add WhatsApp → resurrect channel abstraction *at the `ai_caller/` level*, reference this doc for the pattern.

---

## Review cadence

Quarterly, same cadence as `mystery_shopper/README.md` review. If the referenced source files have moved or been deleted, update the section headers or mark the pattern as frozen. This file is load-bearing for the "no runtime coupling" contract.
