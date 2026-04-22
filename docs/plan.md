# Rivorix Engineering Plan — UTS Demo · April 30 2026

**Version:** 2.0
**Status:** Active. Supersedes v1.0 and `demo.md` v2.0.
**Owner:** CTO
**Primary audience:** Founders + investors. Engineering uses §4–§6 as the working reference.
**Deadline:** Demo day Friday 1 May 2026 (Kenneth confirmed end-of-April). Code freeze Tuesday 28 April 17:00 MYT.

---

## TL;DR

We commit to the UTS demo as the single forcing function for the next 14 days. Scope: three scenarios (Bahasa First-Touch, Copilot with an orchestrated PIAM miss, Auto-QA + fleet dashboard). Build ceiling: **25 person-days**. The `ai_caller` codebase is our production stack and does not get rewritten. `mystery_shopper/` remains in-repo as a reference implementation — it's the Hilton-proof codebase we mined to design ai_caller, and there are still patterns (scoring prompts, scenario structure, Retell turn-handling) we reference actively. It gets a clean boundary, not a deletion. The strategic claim for investors: ~80% of the output of this demo is reusable capex against any subsequent vertical regardless of how UTS goes.

---

## 1. Strategic context

For the investor-facing read, the important framing is this:

**UTS is a single, concrete test of the BPO-as-buyer thesis.** If Kenneth signs a paid pilot, we have a 1,225-seat Malaysian reference logo and a repeatable playbook into financial BPOs across SEA. If he passes, we have full data on why — answered against three pre-committed discovery questions (§10) — and a production voice+Copilot+QA stack that redirects into healthcare patient recall (Bloom) inside two weeks.

The demo is therefore a forcing function that generates one of two valuable outcomes. Either path compounds the capex.

What we are not doing: betting the company on a single prospect, or building features beyond what the demo needs. The 25 person-day ceiling is how we enforce that.

---

## 2. Goal

By demo day, Kenneth Woo and anyone he brings walks out having seen a working AI outbound pipeline on UTS context, in Bahasa Malaysia, with PIAM compliance flags firing live, and commits to scope a paid pilot within 10 business days.

We also walk out with answers to three discovery questions (§10) regardless of the demo outcome. Those answers determine our next move more than Kenneth's enthusiasm does.

---

## 3. Repo structure — one product, one reference

The repo currently has three codebases. By Tuesday 22 April it has one product (`ai_caller/`) and one clearly-scoped reference (`mystery_shopper/`).

### 3.1 What stays active — `ai_caller/`

Production stack. No refactors until after the demo.

```
ai_caller/
├── pipeline.py           # Twilio audio pipeline
├── web_session.py        # Browser voice session
├── stt.py                # Deepgram streaming STT
├── tts.py                # ElevenLabs streaming TTS
├── llm.py                # GPT-4o streaming wrapper
├── smart_turn.py         # End-of-turn detection
├── phone_fx.py           # Phone-line audio effects
├── audio_utils.py        # μ-law conversion
├── caller.py             # Twilio outbound initiation
├── storage.py            # SQLite persistence
├── config.py             # Env config
├── copilot.py            # Bus + session attach
├── compliance.py         # Rule-pack-agnostic engine
├── qa_engine.py          # Scorecard + fleet aggregation
├── synth_data.py         # Synthetic call generator
├── main.py               # FastAPI shell
└── static/
    ├── copilot.html      # Copilot 3-panel UI
    ├── qa.html           # Scorecard + fleet UI
    └── web_call.html     # Browser voice test UI
```

The compliance engine is rule-pack agnostic, the QA engine runs on any transcript, and the agent JSON pattern means new verticals are config, not code. These are the real assets.

### 3.2 What stays as reference — `mystery_shopper/`

This is the codebase that produced the Hilton NYC booking demo — the concept proof that got us into UTS in the first place. We mined it to design `ai_caller/`, and there are still patterns we reference actively:

- The Retell agent prompt structure for natural turn-taking
- The `criteria: list[dict]` scoring schema in `scoring/engine.py`
- The persona-based scenario configuration pattern
- The channel abstraction (phone/email/webchat) — relevant if we ever return to inbound

**New rules for `mystery_shopper/`:**
- Lives at repo root, clearly labeled as reference — no ambiguity about what's product
- Add a top-of-README banner: *"Reference implementation only. Not a Rivorix product. Do not import from `ai_caller/`."*
- Excluded from CI, deploys, and any shared infra
- No new features, no dependency bumps, no refactors
- If a pattern is worth keeping permanently, port it into `docs/references/` as a distilled snippet rather than reaching into the folder at runtime
- Quarterly review: if we haven't opened it in 90 days, archive to a sibling repo

The `app/` directory (the second mystery-shopper implementation) is different — it's an unfinished duplicate of `mystery_shopper/`. Archive `app/` to a sibling repo this week. Keep one reference, not two.

### 3.3 Cleanup actions this week

```bash
# From repo root
mkdir -p docs/references
mkdir -p docs/archive

# Archive the duplicate mystery-shopper v2
git mv app/ ../rivorix-archive/app/

# Keep the working reference but label it
# (manual: add REFERENCE banner to mystery_shopper/README.md)

# Root-level JS belongs to mystery_shopper — move it under that dir
git mv retell-bundle.js mystery_shopper/
git mv package.json mystery_shopper/
git mv package-lock.json mystery_shopper/

# Strategy doc rationalization
git mv demo.md docs/archive/demo-v2.md
git mv pivot.md docs/pivot.md
git mv SPEC.md docs/archive/SPEC.md

# Extract learnings (manual, 30 min of writing)
# docs/references/mystery_shopper_learnings.md — prompts, scoring, patterns
# docs/references/hilton_demo.mp4 — the recording itself

git commit -m "Scope mystery_shopper as reference; archive app/; move docs"
```

### 3.4 Deferred

Build nothing below before April 30:

- Multi-tenant infra, billing, auth, admin dashboards
- Dialer integrations (Genesys, Avaya, Five9) — we integrate on top
- WhatsApp follow-up channel
- Batch calling, CSV upload, retry logic
- EMR / CRM integrations
- Bloom scenarios (engine supports them via JSON; we don't pre-build)
- Mandarin voice variant (add only if Kenneth explicitly asks)
- Inbound "Engage" framing

### 3.5 What gets built for April 30

Detailed timeline in §4. Build list summary:

1. Bahasa Malaysia UTS agent scenario (credit-card balance transfer)
2. PIAM compliance pack v0 for consumer credit
3. Hero-call synthetic transcript + 100-call synthetic fleet
4. Copilot coaching-card triggers for Bahasa + code-switched register
5. `/demo` launcher page
6. Fallback artifacts folder
7. Three PDF 1-pagers: architecture, PIAM coverage, pilot scope
8. `ask_kenneth.md` — the three discovery questions

---

## 4. Two-week sprint plan

Hard ceiling: **25 person-days across the team.** If we hit day 25 with anything broken, we cut. Dry runs are non-negotiable.

### Week 1 — April 21–27 · "Make it work"

| Day | Deliverable | Owner | Status gate |
|-----|-------------|-------|-------------|
| Mon 21 | Repo cleanup (§3.3) complete. Stack lock (STT/TTS/LLM frozen). Native Malay speaker confirmed on-team or contracted. | CTO + CEO | Repo has one active product dir + one clearly-labeled reference |
| Mon 21 | Bahasa script v1 drafted (balance-transfer, with orchestrated compliance miss) | Malay-native reviewer | Script reviewed by at least one outside Malay speaker |
| Tue 22 | Agent JSON: `agents/uts_bt_bahasa.json` + voice A/B test (3 candidate voices) | Voice lead | Voice chosen; 3 Malay speakers say "could be a call-center agent" |
| Tue 22 | PIAM compliance pack v0 (`compliance/piam_consumer_credit_v0.json`) — 8–12 rules | ML + compliance | Engine loads pack, flags render on existing UI |
| Wed 23 | Warm-transfer mechanism end-to-end (voicemail, "not a good time," transfer, DNC) | Voice lead | Each branch completes without orphan state |
| Wed 23 | Copilot coaching-card triggers for code-switched Bahasa (`mahal`, `kena fikir dulu`, `tanya husband`, etc.) | ML | Cards fire <2s after trigger phrase |
| Thu 24 | `/demo` launcher page wired: caller UI + Copilot + QA opened in orchestrated layout | Frontend | Single click opens the full demo |
| Thu 24 | Synthetic fleet: 100 calls generated, scored, in `calls.db` with `is_synthetic=1` | ML | Fleet dashboard populated, loads <1s |
| Fri 25 | **End-to-end dry run #1** — everything on one story, ugly but working | All | Full flow completes once without human intervention |
| Sat–Sun 26–27 | Bug fix window; Bahasa voice polish | Voice + frontend | No new features |

### Week 2 — April 28 – May 1 · "Make it good"

| Day | Deliverable | Owner | Status gate |
|-----|-------------|-------|-------------|
| Mon 28 | Integration + polish. **Code freeze 17:00 MYT.** No features after this. | All | Feature-complete |
| Tue 29 | **Dry run #2** — CEO + CTO, full presenter flow, timed | All | Run completes in ≤20 minutes |
| Wed 30 | **Dry run #3** — with a native Malay speaker who's never seen the product | All | Rating ≥ 4/5 on voice naturalness |
| Wed 30 | Fallback artifacts folder finalized | Frontend | All 7 fallback scenarios in §8 have artifacts on disk |
| Thu | Final dry run + full demo recording (fallback video) | All | Recording saved, timestamped |
| Thu | Four follow-up emails drafted (outcomes A/B/C/D, §9) | CEO | In drafts folder, ready to send |
| Thu | PDFs printed (architecture, PIAM coverage, pilot scope) | CTO | 3 hard copies |
| **Fri 1 May — Demo day** | Demo + 30-min post-demo retro same day | CEO + CTO | Retro notes in Notion before end of day |

### Hard cut rules

If by **Wednesday 29 April** anything below is broken, cut it:

- Fleet dashboard (Scenario C) → show single-call scorecard only
- Warm-transfer (Scenario A) → show pre-recorded transfer flow
- Orchestrated compliance miss (Scenario B) → narrate over pre-recorded clip

Two scenarios that work beat three that stutter.

---

## 5. File-level change list

New files to create:

```
ai_caller/
├── agents/
│   ├── uts_bt_bahasa.json              # NEW — hero agent
│   └── brands/
│       └── uts_insurance.json           # NEW — brand wrapper
├── compliance/
│   └── piam_consumer_credit_v0.json     # NEW — PIAM rule pack
├── demo_fallbacks/                      # NEW — gitignored content
│   ├── README.md
│   ├── hero_call_audio.wav
│   ├── hero_scorecard.json
│   ├── compliance_flag_clip.mp4
│   └── full_demo_recording.mp4
├── scripts/
│   └── demo_launch.py                   # NEW — one-command demo bootstrap
└── DEMO_RUNBOOK.md                      # NEW — day-of stage directions

docs/
├── architecture.md                      # NEW — 1-pager source
├── piam_coverage.md                     # NEW — 1-pager source
├── pilot_scope.md                       # NEW — pilot proposal source
├── ask_kenneth.md                       # NEW — the 3 discovery questions
├── pivot.md                             # MOVED from root
├── references/                          # NEW
│   ├── mystery_shopper_learnings.md     # Distilled patterns
│   └── hilton_demo.mp4                  # The original proof
└── archive/
    ├── demo-v2.md                       # MOVED
    └── SPEC.md                          # MOVED
```

Files to modify (lightly — no rewrites):

- `ai_caller/main.py` — add `/demo` launcher route (already scaffolded)
- `ai_caller/compliance.py` — verify multilingual regex handling for Malay triggers
- `ai_caller/stt.py` — confirm `language="multi"` for code-switch
- `ai_caller/static/copilot.html` — one styling pass on Bahasa rendering
- `mystery_shopper/README.md` — add reference-only banner

---

## 6. Decisions needed by Monday 21 April EOD

Each blocks downstream work. Named owner, written answer in Notion.

| # | Decision | Owner | Why it blocks |
|---|----------|-------|---------------|
| 1 | Malay-native on team? If no, we contract this week. Budget cap RM 2,500. | CEO | Blocks scenario JSON writing |
| 2 | ElevenLabs tier — PVC Bahasa voice clone, or stay on Azure/multilingual default? | CTO | Blocks voice A/B testing |
| 3 | Ask Kenneth one more time this week for a call recording, or run full synthetic? | CEO | Blocks synth_data scaling decision |
| 4 | Synthetic fleet size — 100 or 500 calls (500 is 5× LLM cost) | CTO | Blocks Thursday synth generation |
| 5 | Demo location — UTS office in KL, or virtual? | CEO | Equipment & travel logistics |
| 6 | Pilot pricing range — enter room with a number, or scope later? | CEO + CTO | Blocks pilot scope PDF drafting |
| 7 | `app/` archive location — new repo name, GitHub org, owner? | CTO | Blocks Monday cleanup |

No decisions on Monday = build stops. Hard rule.

---

## 7. Risk register

| # | Risk | Prob | Impact | Owner | Mitigation |
|---|------|------|--------|-------|------------|
| 1 | Bahasa voice sounds machine-translated; Kenneth notices in 10s | Med | Critical | Malay-native reviewer | Native-speaker dry run Wed W2; fallback to pre-recorded hero audio |
| 2 | Copilot latency >2s (breaks real-time claim) | Med | High | ML lead | Measured every dry run; fallback to pre-rendered coaching clip |
| 3 | QA scorecard generation >30s on demo day | Low | Medium | ML lead | Pre-computed scorecard on disk; "here's what just ran" framing |
| 4 | Orchestrated compliance miss doesn't fire live | Med | Medium | Frontend + ML | Script presenter's recovery line; cut to recorded clip |
| 5 | Internet drops mid-demo | Low | Critical | CTO | Mobile hotspot on-site; full demo video as absolute fallback |
| 6 | Kenneth brings compliance person who challenges PIAM v0 | Med | Medium | CEO | Frame v0 as "co-developed with your team in week 1 of pilot" |
| 7 | Kenneth sends no call recording | High | Low | CEO | Synthetic flow is default; frame as "give us your audio, 48h rerun" |
| 8 | UTS dialer/CCaaS makes integration look hard | Med | High | CTO | "We sit on top, no rip-and-replace" — rehearsed answer |
| 9 | Overbuild, hit 30+ person-days, cost ourselves the next quarter | High | Medium | CTO | 25-day ceiling enforced; Scenario C cut before we break ceiling |
| 10 | Kenneth ghosts regardless of demo quality | Med | High | CEO | 3 discovery questions asked anyway — data captured either way |

---

## 8. Fallback and rehearsal plan

Every demo component has a pre-rendered artifact on disk. Frontend lead owns `demo_fallbacks/` and audits Thursday of Week 2.

| If this breaks... | We cut to... |
|-------------------|--------------|
| Internet | `full_demo_recording.mp4`, narrated live |
| Live call audio | Pre-recorded hero call played through Copilot |
| Bahasa voice | Pre-recorded Puan Aminah audio file |
| QA engine latency | `hero_scorecard.json` opened directly |
| Warm-transfer fails | "In production this is one click" + pre-staged Copilot |
| Compliance flag misses | "Let me show you what this looks like" + clip |
| Fleet dashboard fails to load | Screenshot displayed as image |
| Kenneth sends no recording | Synthetic flow default; post-demo 48h rerun offer |

Three dry runs, non-negotiable: technical (Fri W1), presenter-timed (Tue W2), native-speaker (Wed W2).

---

## 9. Post-demo decision tree

All four follow-up emails drafted by Thursday of Week 2.

### Outcome A — Strong yes (pilot scoping scheduled within 10 days)

- Pilot-scope PDF within 24h
- Scoping call within 10 business days
- Hold Bloom option warm; don't accelerate
- Draft DPA + security questionnaire answers

### Outcome B — Soft yes ("impressed, but...")

- Architecture + compliance coverage PDFs within 24h
- Reduced-scope pilot offered (Copilot only, no QA)
- Specific ask in 7 days: send one recording, 48h turnaround
- Max 2 follow-ups in 30 days

### Outcome C — Polite no

- Thank-you + 1-page summary within 24h
- Log learnings: what feature did he implicitly ask for that we don't have?
- No outreach for 90 days
- Bloom reactivated as primary path per `docs/pivot.md`

### Outcome D — Technical failure on demo day

- Same-day honest email + working recording
- Re-demo within 10 days (virtual)
- CTO post-mortem within 48h

---

## 10. Three discovery questions — ask regardless of outcome

More important than the demo itself. CEO asks in the meeting or follow-up, whichever lands naturally:

1. **Tooling authority.** "When you add dialer / QA / agent-assist, is that UTS's call or your bank/insurer client's specification?"
2. **Current QA spend.** "Roughly what % of calls does UTS QA today — in-house or outsourced — and what's it costing?"
3. **Follow-up workflow.** "When a prospect says 'send me details' on a call, what happens in the next 60 minutes?"

Answers in `docs/kenneth_answers.md` same day. These drive pivot/persist/walk more than demo quality.

---

## 11. Reusability audit — what transfers regardless of outcome

The strategic argument for founders and investors: the 25 person-days is capex against *any* subsequent vertical, not just UTS.

| Asset built for UTS | Transfers to Bloom | Transfers to other BPOs | Transfers to direct-to-bank |
|---------------------|--------------------|--------------------------|-----------------------------|
| Voice pipeline | 100% | 100% | 100% |
| Bahasa + code-switch STT | 100% | 100% | 100% |
| Copilot bus architecture | 100% | 100% | 100% |
| Compliance rule engine | 100% | 100% | 100% |
| QA engine + fleet aggregation | 100% | 100% | 100% |
| Agent JSON framework | 100% | 100% | 100% |
| Synthetic data generator | Tool reuse | Tool reuse | Tool reuse |
| Static UIs (Copilot, QA) | Rebrand | Rebrand | Rebrand |

**UTS-specific content that doesn't transfer:**
- `compliance/piam_consumer_credit_v0.json` (PIAM-specific rules)
- `agents/uts_bt_bahasa.json` (financial product vocabulary)
- Coaching triggers tuned to credit-card outbound

**Net:** roughly 80% of the 25 person-days is reusable engineering. This is the core argument for running the demo at full scope even under a probability-weighted view of the outcomes.

---

## 12. Kill conditions — UTS path, not Rivorix

We abandon the BPO ICP (not Rivorix) if any of the following hold after the demo:

1. Kenneth's answer to Discovery Question #1 is "our bank/insurer clients pick the tools." BPOs aren't the buyer; banks are — different sales motion, different startup, not a 1,000-seat pilot in 90 days.
2. No paid pilot scoped within 30 days of demo.
3. Kenneth's scope request exceeds 90 days of build on current team.
4. Bank-grade compliance certification (SOC 2, ISO 27001) becomes a gate we can't credibly commit to in 6 months.

If any kill fires, we pivot to Bloom per `docs/pivot.md` within 2 weeks. The code is already 80% ready; we lose time, not capex.

---

## 13. This week's priorities — in order

**Monday 21:**
1. Repo cleanup (§3.3) — before anything else
2. 7 decisions resolved (§6)
3. Bahasa script v1 drafted

**Tuesday 22:**
4. PIAM rule pack scaffolded
5. First Bahasa voice test recorded

**Wednesday 23:**
6. Warm-transfer mechanism end-to-end
7. 3 discovery questions sent to Kenneth separately (not buried in demo prep)

Monday slippage blocks everything. If we can't hit Monday, we ship 2 scenarios and negotiate a 1-week slip with Kenneth — CEO's call, made Monday EOD.

---

## 14. Investor-facing summary

For the founder/investor read, three points that matter beyond the demo itself:

**Market thesis test:** UTS is a single, concrete instance of the BPO-as-buyer thesis — whether mid-market Malaysian BPOs pick their own AI tools or have them specified by bank/insurer clients. The discovery questions (§10) generate the answer regardless of pilot outcome. That answer has direct implications for TAM, sales cycle, and ICP.

**Capital efficiency:** 25 person-days against a production asset that transfers to two other verticals with ~80% reuse. No code is thrown away. If UTS converts, we have a reference logo; if not, we're 2 weeks from Bloom pilot-ready.

**Execution discipline:** hard build ceiling, hard code freeze, written kill conditions, four pre-drafted follow-up emails. The company's internal operating standard scales from here. This is the first time we've run a deliverable of this scope with a published kill criterion; we treat it as a repeatable pattern.

---

**Document ends. Version-control this file. Updates require CTO sign-off.**

---

Two things before engineering picks this up Monday:

First, decisions 1, 2, and 7 in §6 are on you and me — Malay-native on team, ElevenLabs tier, and where `app/` gets archived. These gate Tuesday. Can we resolve them in a 30-minute sync Sunday evening?

Second, the Kenneth recording ask — I'd still send it this week, separately from demo prep comms, framed as "bringing something real to the next conversation." Low cost, asymmetric upside. Want me to draft it?