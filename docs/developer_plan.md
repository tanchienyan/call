# Rivorix UTS Demo — Developer Plan

**Derived from:** `plan.md` v2.0 (CTO, 2026-04-20)
**Audience:** Engineers executing the 14-day sprint to demo day (Fri 1 May 2026)
**Status:** Active. Updated 2026-04-21.
**Code freeze:** Tue 28 Apr 17:00 MYT.
**Ceiling:** 25 person-days total — if we break ceiling, Scenario C (fleet dashboard) gets cut first.

This doc is the working engineering reference. For strategic context / investor framing / kill conditions read `plan.md`. This doc only answers: *what do I build, in what order, and how do I know it's done.*

---

## 0. How to use this doc

1. Start at §2 (current state) — do not rebuild anything marked ✅.
2. Resolve blockers in §3 **today** (Mon 21 Apr). Every blocker gates ≥1 Tue/Wed task.
3. Work §4 top-down by day. Each task has: context · files · acceptance · estimate.
4. §5 is the dry-run SOP. Non-negotiable — three runs, see `plan.md` §8.
5. §6 is the fallback artifact production checklist. Owned by frontend lead.
6. Every step cross-references `plan.md §X.Y` so you can trace strategic intent.

---

## 1. Environment preflight

Before writing any code, verify the machine is sane. This is the *exact* sequence a new contributor runs on day 1.

```bash
cd ~/Desktop/website/mystery/ai_caller
source .venv/bin/activate               # MUST see (.venv) in prompt
python -c "import fastapi, openai, deepgram, elevenlabs, twilio, pipecat; print('ok')"
python main.py                          # uvicorn on :8000
# in another terminal:
curl -s http://localhost:8000/api/health
```

Expected health payload when all providers are keyed:

```json
{"status":"ok","active_calls":0,"twilio":true,"deepgram":true,"elevenlabs":true,"openai":true}
```

**Caveat (known bug):** `/api/health` only checks env-var *presence*, not key validity. Real validity probe lives in §4 Tue-22 task T-4 (harden health endpoint).

### Provider key status (audited 2026-04-21 19:55 MYT)

| Provider | State | Action |
|---|---|---|
| OpenAI | ✅ HTTP 200 | none |
| Deepgram | ✅ HTTP 200 | none |
| ElevenLabs | ❌ HTTP 401 "Free Tier disabled" | **Pay $5/mo Starter at https://elevenlabs.io/app/subscription**, regenerate key with `text_to_speech` + `voices_read` scopes, paste into `ai_caller/.env`, re-run probe. See §3 Blocker B-2. |

### Secret hygiene rules (learned the hard way today)

- `.env` is runtime, gitignored, real values. `.env.example` is template, committed, placeholders only.
- **Never paste a live key into any `.env.example`.** GitHub push protection will reject, and the key must be assumed compromised if it appears anywhere in the diff.
- Verify before every commit: `git diff origin/main -- '**/.env.example'` must show no secret-shaped values.

---

## 2. Ground truth — what's built, what's broken, what's missing

Audited 2026-04-21. Updated every time something flips state.

### 2.1 Already shipped (do not rebuild)

| `plan.md` ref | Deliverable | Evidence |
|---|---|---|
| §3.1, §5 | Production voice pipeline (Twilio + browser) | `ai_caller/pipeline.py`, `web_session.py` |
| §3.1 | Multilingual STT | `stt.py` — Deepgram Nova-3 with per-agent `language` param (en/ms/zh/multi) |
| §3.1 | TTS with auto model select | `tts.py` — Flash v2.5 for EN, Multilingual v2 for ms/zh |
| §3.1 | Compliance engine (rule-pack agnostic) | `compliance.py` — supports `regex_any`, `first_n_turns_must_contain`, LLM rules |
| §3.1 | Smart turn v3.2 (ONNX) | `smart_turn.py` — loads without PyTorch |
| §3.1 | Copilot bus + per-call session | `copilot.py`, `/copilot`, `static/copilot.html` |
| §3.1 | QA scorecard + fleet aggregation | `qa_engine.py`, `/qa`, `static/qa.html` |
| §3.1 | Warm transfer + AI-silence-after-transfer | `[TRANSFER_TO_HUMAN]` marker in `web_session.py`, `transfer.py` |
| §5 | Hero agent config (Bahasa + English) | `agents/uts_bt_bahasa.json`, `agents/uts_bt_en.json` — both include proactive AI-identity disclosure |
| §5 | PIAM rule pack v0 | `compliance/piam_consumer_credit_v0.json` — 9 rules, covers AI-disclosure / recording consent / interest-rate disclosure / pressure tactics (EN+BM+ZH) / opt-out / no false claims / third-party consent / AI scope boundary |
| §5 | Brand wrapper | `agents/brands/uts_insurance.json` + `bloom_healthcare.json`, `cantiq_clinic.json`, `kheng_dental.json` — merged into agent at call time via `_prepare_agent_from_request` in `main.py` |
| §5 | Coaching rules for Bahasa | `coaching/uts_bt_bahasa_v0.json` |
| §5 | Demo launcher | `static/demo.html` + `/demo` route |
| §5 | DB schema migrations + label columns | `storage.py` — `outcome`, `qa_score`, `compliance_flags_json`, `brand_id`, `is_synthetic`, etc. Verified via `PRAGMA table_info(calls)`. |
| §5 | Synthetic call generator (tagged `is_synthetic=1`) | `synth_data.py` |
| §5 | `DEMO_RUNBOOK.md` | `ai_caller/DEMO_RUNBOOK.md` |
| §5 | `demo_fallbacks/README.md` | Placeholder only — real artifacts pending (§6) |
| §5 | Human outcome override endpoint | `PATCH /api/calls/{id}/outcome`, button in `qa.html` |

### 2.2 Broken right now

| ID | Issue | Blast radius | Fix |
|---|---|---|---|
| BUG-1 | ElevenLabs account-level Free-Tier block | TTS dead → no call can complete | §3 Blocker B-2 |
| BUG-2 | `/api/health` reports `true` for dead keys | Misleads operators + demo | §4 Tue-22 T-4 |
| BUG-3 | 100-call synthetic fleet never generated | `/qa` fleet dashboard is empty | §4 Thu-24 T-8 |

### 2.3 Not yet started (per `plan.md` §5 + §3.3)

| ID | Deliverable | Target | Owner |
|---|---|---|---|
| TODO-1 | Repo cleanup — archive `app/`, move root-level JS into `mystery_shopper/`, relocate strategy docs | Mon 21 | CTO |
| TODO-2 | `docs/` directory + reference banner on `mystery_shopper/README.md` | Mon 21 | CTO |
| TODO-3 | Bahasa script v1 review by outside Malay speaker | Mon 21 | CEO + Malay reviewer |
| TODO-4 | Voice A/B test (3 candidate ElevenLabs voices) | Tue 22 | Voice lead |
| TODO-5 | `scripts/demo_launch.py` one-command bootstrap | Thu 24 | CTO |
| TODO-6 | 100-call synthetic fleet populated in `calls.db` | Thu 24 | ML |
| TODO-7 | `/demo` launcher end-to-end polish (already routed, needs wire-up verification) | Thu 24 | Frontend |
| TODO-8 | Fallback artifacts (§6) | Thu W2 | Frontend |
| TODO-9 | Three 1-pager source markdowns (`docs/architecture.md`, `piam_coverage.md`, `pilot_scope.md`) | Thu W2 | CTO |
| TODO-10 | `docs/ask_kenneth.md` — three discovery questions | Wed 23 | CEO |
| TODO-11 | Three dry runs (§5) | Fri 25 / Tue 29 / Wed 30 | All |
| TODO-12 | Four follow-up email drafts (Outcomes A/B/C/D) | Thu W2 | CEO |

---

## 3. Unblock today (Mon 21 Apr) — blockers gating Tue

Each blocker must have a **written resolution in Notion by 17:00 MYT Monday**, else Tue work stops (per `plan.md` §13 and §6).

### Blocker B-1 — Seven strategic decisions (`plan.md` §6)

Owner: CEO + CTO. Written answers in Notion. Summarized here so engineers don't get blocked:

1. Malay-native reviewer — on team or contract? → gates TODO-3, TODO-4.
2. ElevenLabs tier — Starter $5 or Creator $22 (for PVC voice clone)? → gates B-2 and voice A/B.
3. Kenneth recording — ask again this week? → gates synth volume.
4. Synth fleet size — 100 (default) or 500 (5× OpenAI spend)? → gates TODO-6.
5. Demo location — UTS KL office or virtual? → gates hardware checklist.
6. Pilot pricing — entering the room with a number? → gates `docs/pilot_scope.md`.
7. `app/` archive destination — sibling repo name + GitHub org? → gates TODO-1.

**If decisions 1, 2, 7 are unresolved by Mon EOD, build stops Tue AM.** CTO + CEO must sync Sunday evening (per `plan.md` final note).

### Blocker B-2 — ElevenLabs account

1. CTO pays Starter $5 at https://elevenlabs.io/app/subscription.
2. Regenerate key at https://elevenlabs.io/app/settings/api-keys with these scopes:
   - `text_to_speech`
   - `voices_read`
   - `voice_clone` (only if Creator tier + PVC decision from B-1.2)
3. Paste into `ai_caller/.env` only. Verify `.env.example` still has `sk_...` placeholder.
4. Validate:

```bash
cd ai_caller && .venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv(override=True)
import asyncio, httpx, config
async def p():
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get('https://api.elevenlabs.io/v1/voices',
                        headers={'xi-api-key': config.ELEVENLABS_API_KEY})
        print('voices:', r.status_code, 'count:', len(r.json().get('voices', [])) if r.status_code==200 else r.text[:200])
        r = await c.post(
            'https://api.elevenlabs.io/v1/text-to-speech/XrExE9yKIg1WjnnlVkGX/stream?output_format=pcm_24000',
            headers={'xi-api-key': config.ELEVENLABS_API_KEY, 'Content-Type':'application/json'},
            json={'text':'hello','model_id':'eleven_flash_v2_5'})
        print('tts:', r.status_code, len(r.content) if r.status_code==200 else r.text[:200])
asyncio.run(p())
"
```

Expected: `voices: 200 count: >0`, `tts: 200 <nonzero-bytes>`.

### Blocker B-3 — Malay-native reviewer

Per B-1.1. If contracting: ≤RM 2,500 cap (plan §6). They review:
- `agents/uts_bt_bahasa.json` first_message + system_prompt opening sequence
- Coaching triggers in `coaching/uts_bt_bahasa_v0.json`
- A recorded 60-second sample from ElevenLabs voice A/B (once B-2 clears)

Reviewer delivers a yes/no on "could be a real UTS call-center agent" and a list of wording fixes. Target: voice rating ≥4/5 from three Malay speakers.

---

## 4. Sequenced engineering tasks

Each task: `ID | description | files | acceptance | estimate`. Tasks are ordered by dependency. Skip nothing without CTO sign-off.

### Week 1 — "Make it work"

#### Monday 21 April (cleanup + unblock)

**T-1 — Repo cleanup** (`plan.md` §3.3) — 2h — Owner: CTO

```bash
cd ~/Desktop/website/mystery
mkdir -p docs/references docs/archive

# Archive unfinished duplicate
# Destination per B-1.7 decision. Assume sibling repo rivorix-archive.
git mv app ../rivorix-archive/app      # or: create sibling repo first

# Root-level JS belongs to mystery_shopper
git mv retell-bundle.js    mystery_shopper/
git mv retell-sdk.js       mystery_shopper/
git mv bundle_entry.js     mystery_shopper/
git mv web_call_test.html  mystery_shopper/
git mv package.json        mystery_shopper/
git mv package-lock.json   mystery_shopper/

# Strategy doc rationalization
git mv demo.md             docs/archive/demo-v2.md    2>/dev/null || true
git mv pivot.md            docs/pivot.md
git mv SPEC.md             docs/archive/SPEC.md        2>/dev/null || true
git mv plan.md             docs/plan.md
git mv developer_plan.md   docs/developer_plan.md      # this file

# Reference banner (manual edit, see next task)
# Commit
git commit -m "Scope mystery_shopper as reference; archive app/; relocate docs"
```

**Acceptance:**
- `git ls-tree HEAD --name-only | rg "^(app/|retell|package|bundle|web_call_test|pivot\.md|plan\.md)$"` returns nothing.
- `ls docs/` shows `plan.md`, `developer_plan.md`, `pivot.md`, `references/`, `archive/`.
- `ai_caller/` is untouched.

**T-2 — Reference banner on `mystery_shopper/README.md`** — 10m — Owner: CTO

Prepend:

```markdown
> ⚠️ **REFERENCE IMPLEMENTATION ONLY.** This directory is retained for pattern reference — Retell agent prompt structure, `scoring/engine.py` criteria schema, channel abstraction. **Do not import from `ai_caller/`. Not a Rivorix product.** See `docs/plan.md` §3.2. Quarterly review: archive to a sibling repo if untouched for 90 days.
```

**Acceptance:** banner visible at top of `mystery_shopper/README.md`.

**T-3 — Distill reference patterns** (`plan.md` §3.2) — 30m — Owner: CTO

Create `docs/references/mystery_shopper_learnings.md`. Extract and write down (don't import from the folder at runtime):
- Retell agent prompt opening-sequence template (from `mystery_shopper/agents/*.json` or equivalent)
- `scoring/engine.py` criteria list schema — why `list[dict]` not `dict[str, criterion]`
- Persona-based scenario structure
- Channel abstraction boundary (phone/email/webchat)

**Acceptance:** file exists, ≤500 lines, zero `from mystery_shopper` imports in `ai_caller/`.

**T-4 (optional, preferred Mon) — Harden `/api/health`** — 45m — Owner: CTO

Fix BUG-2. Replace presence-only check with real provider probe, cached 30s.

File: `ai_caller/main.py` around line 538.

Pseudocode shape:

```python
# in-memory cache: {provider: (expires_at, ok)}
_health_cache: dict[str, tuple[float, bool]] = {}
_HEALTH_TTL = 30  # seconds

async def _probe(name: str, url: str, headers: dict) -> bool:
    now = time.time()
    cached = _health_cache.get(name)
    if cached and cached[0] > now:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            r = await c.get(url, headers=headers)
            ok = r.status_code == 200
    except Exception:
        ok = False
    _health_cache[name] = (now + _HEALTH_TTL, ok)
    return ok

@app.get("/api/health")
async def health():
    # Run concurrently
    openai_ok, deepgram_ok, elevenlabs_ok = await asyncio.gather(
        _probe("openai", "https://api.openai.com/v1/models",
               {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}),
        _probe("deepgram", "https://api.deepgram.com/v1/projects",
               {"Authorization": f"Token {config.DEEPGRAM_API_KEY}"}),
        _probe("elevenlabs", "https://api.elevenlabs.io/v1/voices",
               {"xi-api-key": config.ELEVENLABS_API_KEY}),
    )
    return {
        "status": "ok" if all([openai_ok, deepgram_ok, elevenlabs_ok]) else "degraded",
        "active_calls": len(active_sessions),
        "twilio":     bool(config.TWILIO_ACCOUNT_SID),
        "deepgram":   deepgram_ok,
        "elevenlabs": elevenlabs_ok,
        "openai":     openai_ok,
    }
```

**Acceptance:** with a deliberately broken ElevenLabs key, `/api/health` returns `"elevenlabs": false` within 2s, and `"status": "degraded"`. `/api/health` response time under load (5 parallel `curl`s) stays under 100ms thanks to cache.

**T-5 — Bahasa script v1 review** (`plan.md` §4 Week 1 Mon) — async — Owner: CEO + reviewer

No engineering work; CEO delivers reviewed copy by Tue AM. Engineers wait for updated `agents/uts_bt_bahasa.json` text.

---

#### Tuesday 22 April (voice + compliance polish)

**T-6 — Voice A/B test** (`plan.md` §4 Week 1 Tue) — 3h — Owner: voice lead

Generate 60s Bahasa samples for 3 candidate `voice_id`s against the current `uts_bt_bahasa.json` first_message:

1. `wIwafQRMRzBqGgHCoUm0` (Jawid Iqbal — listed in `web_call.html` as "Calm podcast host, Malaysian male")
2. `cALE2CwoMM2QxiEdDEhv` (Valentine — "Serious, neutral, SE Asian male")
3. One PVC-cloned voice if B-1.2 selected Creator tier; else a third ElevenLabs library voice (Malay speakers underrepresented — check the voice library filter for "Malay" or "Indonesian").

Script:

```bash
cd ai_caller && .venv/bin/python -c "
import asyncio, httpx, config, pathlib
SAMPLE = ('Selamat pagi, boleh saya bercakap dengan Puan Aminah? Saya Nurul, '
          'pembantu AI dari UTS Card Services. Panggilan ini untuk berkongsi '
          'satu tawaran pemindahan baki kad kredit.')
async def gen(voice_id, out):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=mp3_44100_128',
            headers={'xi-api-key': config.ELEVENLABS_API_KEY, 'Content-Type':'application/json'},
            json={'text': SAMPLE, 'model_id': 'eleven_multilingual_v2',
                  'voice_settings': {'stability':0.35,'similarity_boost':0.75,'style':0.2}})
        out.write_bytes(r.content)
        print(f'wrote {out} ({len(r.content)} bytes)')
outdir = pathlib.Path('demo_fallbacks/voice_ab'); outdir.mkdir(parents=True, exist_ok=True)
asyncio.run(asyncio.gather(
    gen('wIwafQRMRzBqGgHCoUm0', outdir/'jawid.mp3'),
    gen('cALE2CwoMM2QxiEdDEhv', outdir/'valentine.mp3'),
))
"
```

Play all three to three Malay speakers. Rank 1–5 on: natural prosody, accent authenticity, "could be a UTS call-center agent." Winner's `voice_id` goes into `agents/brands/uts_insurance.json` as `default_voice_id`, or overrides `agents/uts_bt_bahasa.json.voice_id`.

**Acceptance:** written scorecard from ≥3 Malay speakers. Winner rated ≥4/5 on "could be a real agent."

**T-7 — Compliance pack polish** (`plan.md` §4 Week 1 Tue) — 1h — Owner: ML

`compliance/piam_consumer_credit_v0.json` already has 9 rules. Verify against PIAM/BNM 2024 consumer-credit guidelines:
- Add any missing rule up to 12 (plan specifies "8–12 rules")
- Add BM + ZH trigger phrases to any rule that's currently EN-only
- Validate each `regex_any` pattern against a handcrafted transcript in a test cell

Smoke test (copy-paste):

```python
from dotenv import load_dotenv; load_dotenv()
from compliance import CompliancePack, LiveComplianceTracker
pack = CompliancePack.load('piam_consumer_credit_v0')
tr = LiveComplianceTracker(pack)
# Happy path — agent discloses AI in first turn, consent in turn 3
tr.on_turn('agent', 'Hai Puan, saya pembantu AI dari UTS.')
tr.on_turn('user',  'Ya.')
tr.on_turn('agent', 'Panggilan ini direkod untuk tujuan kualiti. Setuju?')
# expected: ai_identity_disclosure -> satisfied, recording_consent still pending LLM audit
print({rid: f.status for rid, f in tr.flags.items()})
```

**Acceptance:** engine loads pack without error; live regex rules fire correctly on handcrafted BM / ZH / EN triggers. Copilot UI shows flags rendering in `static/copilot.html` — styling pass deferred to T-10.

**T-8 — Warm-transfer end-to-end** (`plan.md` §4 Week 1 Wed — pull forward to Tue PM if time allows) — 3h — Owner: voice lead

Already implemented at the code level. What's needed is **branch verification** — each of the four outcomes must complete cleanly without orphan state:

1. Voicemail → STT sees voicemail menu prompt → agent hangs up within 3s.
2. "Not a good time" → agent acknowledges → logs `outcome=callback_requested`.
3. Transfer (`[TRANSFER_TO_HUMAN]`) → AI goes silent → human closer takes over → verified by `transferred` flag in `web_session.py`.
4. DNC ("don't call me again") → agent confirms opt-out → logs `outcome=opted_out`.

Test matrix:

```
scenario        | trigger phrase (BM)                     | expected log
----------------|------------------------------------------|-------------
voicemail       | "anda telah menghubungi mailbox..."      | outcome=voicemail, duration<10s
busy            | "boleh call balik lain kali"             | outcome=callback_requested
transfer        | "ya saya berminat, tolong sambungkan"    | [TRANSFER_TO_HUMAN] in transcript
dnc             | "jangan call saya lagi"                  | outcome=opted_out, dnc_flag=true
```

**Acceptance:** all 4 rows complete without exceptions in server log; `storage.list_calls_with_labels()` shows correct `outcome` for each.

---

#### Wednesday 23 April (Copilot + Kenneth ask)

**T-9 — Copilot coaching triggers for code-switched BM** (`plan.md` §4 Week 1 Wed) — 2h — Owner: ML

`coaching/uts_bt_bahasa_v0.json` exists. Verify it covers the code-switched register typical of Malaysian financial outbound:

| Customer phrase (BM/code-switch) | Intent | Coaching card |
|---|---|---|
| "mahal lah" | price objection | "Acknowledge, pivot to savings vs standard 18% rate" |
| "kena fikir dulu" | stall | "Offer warm transfer to human for details — no pressure close" |
| "tanya husband / tanya wife dulu" | consent objection | "Affirm, offer callback slot, log as callback_requested" |
| "tak minat" | hard no | "Thank, end call, tag opted_out" |
| "dah ada card" | existing product | "Pivot to balance-transfer benefit even for existing holders" |
| "interest rate berapa" | rate question | "Do NOT quote effective rate — this is closer's job. Transfer." |

Measure card latency in a live browser call — each card should surface within **<2s** of STT finalization of the trigger phrase. Instrument with `time.time()` around the publish step in `copilot.py`.

**Acceptance:** ≥6 BM triggers in the rules file; latency measured and logged in `DEMO_RUNBOOK.md`; live test with at least one code-switched phrase fires correctly.

**T-10 — Copilot styling pass** — 45m — Owner: frontend

`static/copilot.html` — one pass specifically for BM text rendering: line-height, soft-break at Malaysian-typical mid-sentence connectors ("kan", "lah", "ya"), Mandarin character fallback font.

**Acceptance:** eye-test with the Malay reviewer from T-5 / T-6.

**T-11 — CEO writes `docs/ask_kenneth.md`** (`plan.md` §10, §13) — 30m — Owner: CEO

The three discovery questions. Sent to Kenneth *separately* from demo prep comms this week. Engineers' job is just to add the file to `docs/`.

**Acceptance:** file exists with three questions verbatim from `plan.md` §10.

---

#### Thursday 24 April (orchestration + synth)

**T-12 — `/demo` launcher verification** (`plan.md` §4 Week 1 Thu, §5) — 1h — Owner: frontend

`/demo` route exists and serves `static/demo.html`. What needs verifying:

- Single click on "Start demo" opens caller UI + copilot UI in correctly-sized windows.
- Both tabs receive the same `call_id` so copilot attaches to the live call.
- `qa.html` opens in a third tab / panel when demo completes.
- Layout works at the demo laptop's resolution.

**Acceptance:** end-to-end click test on demo laptop at demo resolution. No manual URL editing required mid-demo.

**T-13 — `scripts/demo_launch.py`** (`plan.md` §5) — 1h — Owner: CTO

One-command bootstrap:

```bash
python scripts/demo_launch.py
# should: check env, ping providers, init DB, seed synth data if empty, open /demo in browser
```

Minimal implementation (~60 lines):

```python
# scripts/demo_launch.py
import asyncio, os, sys, webbrowser, subprocess
from dotenv import load_dotenv
load_dotenv()
# 1. Provider probes (reuse logic from T-4)
# 2. storage.init_db()
# 3. if storage.count_calls(is_synthetic=True) < 50: run synth_data.generate_fleet(100)
# 4. subprocess.Popen([sys.executable, 'main.py'])
# 5. webbrowser.open('http://localhost:8000/demo')
```

**Acceptance:** fresh checkout → `pip install -r requirements.txt` → `cp .env.example .env && <paste keys>` → `python scripts/demo_launch.py` → demo UI open in browser with all three scenarios reachable.

**T-14 — 100-call synthetic fleet** (`plan.md` §4 Week 1 Thu, fixes BUG-3) — 2h — Owner: ML

`synth_data.py` exists. Run generation:

```bash
cd ai_caller && .venv/bin/python synth_data.py --count 100 --brand uts_insurance --channel voice --language multi
```

Decision B-1.4 sets count: 100 (default) or 500 (5× OpenAI spend — ~$5-10 depending on scorecard depth).

Verify:

```sql
SELECT COUNT(*) FROM calls WHERE is_synthetic=1;        -- expect 100
SELECT outcome, COUNT(*) FROM calls WHERE is_synthetic=1 GROUP BY outcome;
-- expect realistic distribution: ~35% interested, ~20% callback, ~25% not_interested, ~15% voicemail, ~5% opted_out
SELECT AVG(qa_score) FROM calls WHERE is_synthetic=1;   -- expect 0.55-0.85
```

Fleet dashboard `/qa` should render full aggregations in <1s.

**Acceptance:** 100 synthetic calls in DB, fleet dashboard loads <1s, outcome distribution passes eyeball test for realism (no 100% "interested").

**T-15 — `ai_caller/demo_fallbacks/` artifact slots defined** — 30m — Owner: frontend

See §6 below — this task is just the folder-and-slot scaffolding. Actual recording happens Thu W2.

---

#### Friday 25 April — Dry run #1 (technical)

See §5.1. All engineers present. Cadence: ≤90 min including bug triage. Exit criteria: full flow completes once without human intervention.

---

### Week 2 — "Make it good"

#### Monday 28 April — Integration + code freeze

**T-16 — Integration pass** — all day — Owner: all

Triage bugs from dry-run #1. No feature additions after 17:00 MYT. Open `DEMO_RUNBOOK.md` and execute every cue line-by-line. Every "this should happen" that doesn't, file a ticket.

**Code freeze at 17:00 MYT.** The `main` branch at that commit is the demo build. `git tag demo-candidate-v1` at freeze. Any post-freeze change requires explicit CTO sign-off and re-triggers dry run #2.

---

#### Tuesday 29 April — Dry run #2 (presenter-timed)

See §5.2. CEO + CTO only. Stopwatch. Exit criteria: run completes in ≤20 minutes.

Hard-cut deadline (per `plan.md` §4 hard-cut rules): if anything below is still broken by end of today, cut:
- Fleet dashboard → show single-call scorecard only.
- Warm-transfer → show pre-recorded transfer flow.
- Orchestrated compliance miss → narrate over pre-recorded clip.

---

#### Wednesday 30 April — Dry run #3 (native speaker)

See §5.3. Malay native who has never seen the product. Exit criteria: rating ≥4/5 on voice naturalness.

Also Wed 30:
- **T-17 — Fallback artifact freeze** (§6) — all artifacts on disk, owner sign-off — frontend.
- **T-18 — CTO prints three 1-pager PDFs** (`plan.md` §5): `docs/architecture.md`, `docs/piam_coverage.md`, `docs/pilot_scope.md` → PDF → 3 hard copies each.

---

#### Thursday 30 April — Final rehearsal + safety net

- **T-19 — Final full dry run** — 90 min — all. Record it; the recording is `demo_fallbacks/full_demo_recording.mp4` (the absolute fallback per `plan.md` §8 row 1).
- **T-20 — CEO drafts four follow-up emails** (Outcomes A/B/C/D, `plan.md` §9). Saved in drafts, not sent. Subject lines:
  - A — "Re: UTS pilot scope — proposal attached"
  - B — "Re: today's demo — quick scoped starting point"
  - C — "Re: today's demo — thanks for the time"
  - D — "Re: today's demo — technical recap + working recording"

---

#### Friday 1 May — Demo day

1. **Morning (09:00 MYT):** full env check, run `scripts/demo_launch.py`, confirm `/api/health` returns `"status":"ok"` with three green providers.
2. Hardware: hotspot on, demo laptop on, secondary laptop with `full_demo_recording.mp4` cued.
3. **Demo.**
4. **Post-demo retro (30 min, same day)** — CEO + CTO. Notes written in Notion before EOD. Include: which of `plan.md` §10 questions got answered, which didn't, and the corresponding `plan.md` §12 kill check.

---

## 5. Dry run SOPs

Three dry runs. Each has a fixed exit gate (from `plan.md` §4, §8). If the gate fails, re-run within 24h.

### 5.1 Dry run #1 — Technical (Fri 25 Apr, 14:00 MYT, ≤90 min)

**Setup (15 min)**
1. Fresh terminal — kill any stale Python.
2. `cd ai_caller && source .venv/bin/activate && python main.py`.
3. Open `http://localhost:8000/demo` in primary Chrome window.
4. Start a browser call — **Scenario A**: Bahasa First-Touch, use `agents/uts_bt_bahasa.json`, brand `uts_insurance`.
5. Speak Malay as the customer persona. Hit every branch: confirm identity, grant recording consent, ask one objection ("mahal lah"), agree to transfer.

**Run (45 min)**
- Scenario A: complete flow → verify Copilot coaching card fires, `ai_identity_disclosure` marked satisfied, `pressure_tactics` not fired.
- Scenario B: run again, this time as the human closer — discuss interest rate without proper disclosure → verify the `interest_rate_disclosure` flag fires on Copilot in red.
- Scenario C: open `/qa` → verify fleet dashboard renders 100 synth calls + today's real call at the top.

**Triage (30 min)** — file tickets for anything that stuttered.

**Exit gate:** full flow completed once without human intervention. If it didn't, re-run Sat/Sun.

### 5.2 Dry run #2 — Presenter-timed (Tue 29 Apr, ≤20 min)

**CEO presents as if Kenneth is in the room.** CTO operates the laptop.

- Stopwatch from "hello" to "any questions."
- Target: 20 min total. 6 min Scenario A, 6 min Scenario B, 5 min Scenario C, 3 min wrap + pilot ask.
- **No bug fixing during the run.** Notes only. Fix after.

**Exit gate:** run completes in ≤20 min without presenter falling behind stagecues in `DEMO_RUNBOOK.md`.

### 5.3 Dry run #3 — Native speaker (Wed 30 Apr)

**Malay-native external reviewer** (≠ the script reviewer) watches Scenario A live. Does not know the product.

- Record voice. Score on: prosody (1-5), accent authenticity (1-5), "could this be a real UTS agent" (y/n).
- Debrief 15 min. Capture: what jumped as obviously-AI, what worked.

**Exit gate:** naturalness rating ≥4/5. Below that → fallback to pre-recorded hero audio (per `plan.md` §8 row 3) and update `DEMO_RUNBOOK.md` accordingly.

---

## 6. Fallback artifact production — `ai_caller/demo_fallbacks/`

Every live demo component has a pre-rendered artifact on disk. Frontend lead owns. Audit Thu W2. See `plan.md` §8.

`demo_fallbacks/` is gitignored (per `.gitignore`) — artifacts are produced locally, shared via a pinned Dropbox/Drive folder (TBD by CTO).

| File | Content | How to produce |
|---|---|---|
| `full_demo_recording.mp4` | 20-min screen recording of the complete demo | QuickTime screen capture during dry run #3 |
| `hero_call_audio.wav` | Scenario A full audio, export at 44.1kHz | Capture during dry run #2; ffmpeg join if split |
| `hero_scorecard.json` | Matches `hero_call_audio.wav` — output of `qa_engine.score_call()` | Run `qa_engine` against the dry-run call_id; copy resulting JSON |
| `compliance_flag_clip.mp4` | 30-sec screen-cap of Scenario B flag firing in Copilot | QuickTime on Scenario B during dry run #1 |
| `fleet_dashboard.png` | Screenshot of `/qa` fleet view | macOS ⌘⇧4 during dry run #2 |
| `pre_recorded_transfer.mp4` | "In production this is one click" + Copilot staged | Record during Scenario A dry run, slice at `[TRANSFER_TO_HUMAN]` |
| `voice_ab/*.mp3` | Three BM voice candidates (see T-6) | Already produced in T-6 |

**Acceptance gate (Wed 30 Apr 17:00 MYT):** frontend lead runs through `plan.md` §8 fallback table row-by-row and confirms each has an artifact. Sign-off in Notion.

---

## 7. Output bundle — what goes to Kenneth

Per `plan.md` §5 and §9, the Thursday-W2 output bundle:

| Artifact | Source | Format |
|---|---|---|
| `docs/architecture.md` → PDF | Diagram of voice pipeline + Copilot + compliance + QA | 1 page, landscape |
| `docs/piam_coverage.md` → PDF | Table: each of the 9 PIAM rules × live/LLM detection × severity | 1-2 pages |
| `docs/pilot_scope.md` → PDF | 30-day paid pilot proposal. Pricing from B-1.6 decision. | 1 page |
| `docs/ask_kenneth.md` | Three discovery questions (§10) — **sent separately before demo, not part of bundle** | Email body |

Write these in Markdown in `docs/`. Render to PDF via `pandoc` or `md-to-pdf` (frontend lead's call — we're not shipping a design tool, plain is fine).

---

## 8. Post-demo engineering (Outcome-gated)

Per `plan.md` §9. Engineering backlog for each outcome:

### Outcome A — Strong yes

1. Pilot scope refinement (CEO leads, CTO sizes).
2. DPA + security questionnaire drafts — start from `docs/piam_coverage.md` and extend with data-flow diagram.
3. Kick-off batch-calling build (deferred from `plan.md` §3.4) — CSV upload, retry logic. 5 person-days.
4. Keep Bloom warm but do not accelerate. Healthcare agent scenarios already exist (`agents/brands/bloom_healthcare.json`, `cantiq_clinic.json`, `kheng_dental.json`) — no new code until UTS pilot signed.

### Outcome B — Soft yes

1. Reduced-scope pilot: Copilot-only. Cut QA from pilot scope, not from codebase.
2. 7-day ask: "send one recording, 48h turnaround." CTO builds a one-off ingest script for their call audio format.
3. Max 2 follow-ups in 30 days — CEO's cadence, engineering just provides the rerun artifact.

### Outcome C — Polite no

1. Engineering backlog pivots to Bloom per `docs/pivot.md`.
2. Port UTS learnings: swap `compliance/piam_consumer_credit_v0.json` for a MOH/medical-practice-focused pack (new file, same engine).
3. Swap `agents/uts_bt_bahasa.json` for the six Bloom scenarios already scaffolded in `plan.md` (per the always-applied workspace rule — phase 1 of the healthcare pivot).
4. No UTS outreach for 90 days.

### Outcome D — Technical failure on demo day

1. Post-mortem within 48h — CTO writes. Root-cause + prevention + which dry-run gate missed it.
2. `full_demo_recording.mp4` goes out same-day with an honest email (CEO drafts from Outcome-D template).
3. Re-demo within 10 days (virtual).
4. Re-run the full dry-run sequence before re-demo. No shortcuts.

---

## 9. Reference — `plan.md` section map

Quick lookup when this doc points at `plan.md §X`:

| plan.md § | Topic | This doc maps to |
|---|---|---|
| §1 | Strategic context | (not engineering — read it anyway) |
| §2 | Goal | §0, §7 |
| §3 | Repo structure | §4 T-1 through T-3 |
| §4 | Two-week sprint | §4 day-by-day |
| §5 | File-level change list | §2.3 TODO table + §4 tasks |
| §6 | Decisions needed | §3 Blocker B-1 |
| §7 | Risk register | §5 (dry runs mitigate most), §6 (fallback artifacts mitigate the rest) |
| §8 | Fallback and rehearsal | §5, §6 |
| §9 | Post-demo decision tree | §8 |
| §10 | Three discovery questions | §4 T-11 |
| §11 | Reusability audit | §8 (Outcome C explicit re-use path) |
| §12 | Kill conditions | Post-demo retro gate |
| §13 | This week's priorities | §3, §4 Mon/Tue/Wed |
| §14 | Investor summary | (not engineering) |

---

## 10. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-04-21 | Initial developer plan derived from `plan.md` v2.0. Ground-truth audit embedded in §2. | CTO |

Updates to this file require CTO sign-off, per `plan.md` footer.
