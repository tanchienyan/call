# Pivot Strategy: AI-Powered Healthcare Patient Engagement for Southeast Asia

> **CTO Strategy Brief — v2.0 — April 2026**

## TL;DR

We built a production-grade AI outbound calling pipeline (Twilio + Deepgram + GPT-4o + ElevenLabs) that works across any scenario via JSON config. After deep competitive analysis, we're pivoting from generic BPO sales tooling — a crowded, long-cycle enterprise market — into **AI-driven patient recall and engagement for multi-brand healthcare chains in Southeast Asia**. First client: **The Bloom Healthcare Group** (Malaysia, 50+ outlets across Cantiq Clinic and Kheng Dental). No US incumbent operates in this niche. We ship in 3 weeks.

---

## 1. Where We Are Today

### 1.1 Platform Capabilities

The `ai_caller` pipeline is live and scenario-agnostic:

| Layer | Stack | Status |
|-------|-------|--------|
| Telephony | Twilio (PSTN + WebSocket) | Production |
| STT | Deepgram Nova-3, streaming | Production |
| LLM | GPT-4o with sub-500ms TTFT | Production |
| TTS | ElevenLabs Flash v2.5 | Production |
| Turn detection | Custom VAD + silence thresholds | Production |
| Agent framework | JSON configs with Schegloff-style openings, filler words, backchannel, forbidden AI tells | Production |
| Browser testing | WebSocket-based `/test` route, no phone needed | Production |
| Storage | SQLite with full transcript logging | Production |

Four generic scenarios ship today (`appointment_confirm`, `debt_reminder`, `membership_renewal`, `satisfaction_survey`). The architecture is designed so that **new verticals are new JSON files, not new code**. This is the key leverage point for the pivot.

### 1.2 The Road Not Taken: BPO / Teleservices

We evaluated the BPO market through a detailed engagement with **United Tele Service (UTS)** — a publicly listed Malaysian outbound call center (1,225 agents, ~$20M revenue, zero AI adoption). The analysis revealed three problems with pursuing BPOs:

**Long sales cycles.** Enterprise BPOs require 12-18 month proof-of-value cycles, six-figure pilots, and deep CRM integration. UTS's bank clients (Maybank, CIMB, Great Eastern) carry the regulatory risk and must approve every tooling change. We'd be selling through two layers of procurement.

**Crowded positioning.** The AI contact center market ($2.5B in 2024, ~20% CAGR) has well-funded incumbents at every layer: NICE CXone (22% share, acquired Cognigy for $955M), Genesys ($2.4B cloud ARR), Retell AI (10M+ min/month), Synthflow (4.9/5 G2, 200+ integrations), Observe.AI and CallMiner for QA. A seed-stage startup can't out-feature these players on their home turf.

**Misaligned economics.** BPO revenue depends on agent headcount. AI that replaces agents kills the client's business model. AI that merely augments agents delivers incremental value that's hard to price aggressively. Gartner predicts 50% of orgs that planned customer service workforce reductions will abandon those plans by 2027.

The UTS competitive analysis remains valuable context — see **Appendix A** below.

---

## 2. The Opportunity: Healthcare Patient Recall in SEA

### 2.1 The Gap

Our GTM analysis flagged a clear market segmentation:

| Market | Status | Why |
|--------|--------|-----|
| US AI patient recall | **Red ocean** | Luma Health, Klara, Phreesia, Weave, NexHealth — dozens of funded players. Requires HIPAA, US telephony, and competing against established EMR integrations. |
| SEA AI patient recall (WhatsApp-first) | **Wide open** | No US incumbent operates here. Different regulatory regime (PDPA, not HIPAA). WhatsApp is the default communication channel, not SMS. Private healthcare chains are growing rapidly but run on manual recall. |

The specific wedge: **AI-powered voice and message outreach for patient recall at multi-brand healthcare chains in Malaysia, Singapore, and Thailand.** Voice calling is the entry point (our existing pipeline); WhatsApp Business API is the expansion path.

### 2.2 Why Malaysia First

- **Regulatory advantage.** Malaysia's PDPA (2010, amended 2024) is lighter than HIPAA — no AI-specific voice disclosure statute, no class-action environment. Compliance is achievable at startup scale.
- **Language fit.** Business conducted in English, Malay, and Mandarin — Deepgram Nova-3 supports all three, and ElevenLabs `eleven_multilingual_v2` handles the TTS side.
- **WhatsApp penetration.** 97% of Malaysian smartphone users are on WhatsApp. Patient communication happens there, not via SMS or patient portals.
- **Growing private healthcare.** Malaysia's private healthcare market is expanding at ~12% CAGR, driven by medical tourism and rising middle class. Chains are consolidating and need operational tooling.

### 2.3 Bloom Healthcare Group — First Client

| Attribute | Detail |
|-----------|--------|
| Parent brand | The Bloom Healthcare Group |
| Sub-brands | **Cantiq Clinic** (aesthetics), **Kheng Dental** (dental) |
| Outlets | 50+ across Malaysia |
| Patient base | Est. 50,000-150,000 active patients across brands |
| Current recall method | Manual staff calls, WhatsApp messages, or nothing |
| Primary pain point | Lapsed patients = lost recurring revenue |

**Treatment recall is the highest-ROI scenario.** A dental patient overdue for their 6-month cleaning, or a Botox patient due for a top-up, represents direct revenue recovery. If even 10% of lapsed patients rebook from an AI recall call:

- Average dental cleaning: RM 150-300 (~$35-70)
- Average aesthetics procedure: RM 500-3,000+ (~$115-700)
- 50+ outlets × hundreds of overdue patients each = significant revenue recovered monthly

The ROI story writes itself: "We recovered RM X in lapsed revenue this month. Our service costs RM Y."

### 2.4 Expansion Path

Bloom is the beachhead. The playbook scales to:

| Phase | Target | Market |
|-------|--------|--------|
| Now | Bloom Healthcare Group | Malaysia |
| 6 months | Q&M Dental (100+ outlets), Ko Skin Specialist (10+) | Malaysia / Singapore |
| 12 months | IHH Healthcare (80+ hospitals), Bangkok Dusit Medical | Regional SEA |
| 18 months | Pharma patient adherence programs | Regional SEA |

---

## 3. Product Architecture

### 3.1 Six Healthcare Scenarios (Priority Order)

| # | Scenario | Purpose | Revenue Signal |
|---|----------|---------|----------------|
| 1 | **Treatment Recall** | Proactive outreach for overdue patients (dental checkup, Botox top-up, annual screening) | Direct revenue recovery — highest ROI |
| 2 | **Appointment Reminder** | 24-48h before appointments, with reschedule/cancel handling | Reduces no-shows (industry avg 5-7% → target <2%) |
| 3 | **No-Show Follow-up** | Same-day/next-morning after missed appointment, concerned not accusatory | Recovers missed appointments |
| 4 | **Post-Treatment Follow-up** | 24-72h after procedures, symptom check | Patient safety + satisfaction, brand differentiation |
| 5 | **Patient Satisfaction** | NPS + 3-4 questions, under 2 minutes, 3-7 days post-visit | Operational intelligence for Bloom |
| 6 | **Promo Outreach** | New services, seasonal offers, must identify as promotional early | Upsell channel |

All six scenarios share a healthcare compliance preamble (recording consent, no medical advice, third-party privacy, opt-out handling) and Malaysian English communication style.

**Hard boundaries enforced in every agent prompt:**
- NEVER diagnose, minimize symptoms, or say "that's normal"
- NEVER disclose medical details to third parties
- NEVER pressure patients — offer to have clinic call back
- Always offer opt-out from future calls

### 3.2 Multi-Brand Engine

New `agents/brands/` directory with JSON profiles:

```
bloom_healthcare.json  — parent brand, general wellness tone
cantiq_clinic.json     — premium, warm, aspirational ("going beautifully")
kheng_dental.json      — professional, friendly ("how's everything feeling")
```

Brand config merges into agent behavior at call time: `brand_id` on the API request triggers tone injection, default voice selection, and variable population (outlet address, phone number, etc.). Call-level variables override brand defaults.

### 3.3 Trilingual Pipeline

Each scenario ships in 3 language variants (18 JSON files total):

| Language | STT | TTS Model | Voice Selection |
|----------|-----|-----------|-----------------|
| English | Deepgram Nova-3 `en` | ElevenLabs Flash v2.5 | Existing voice library |
| Bahasa Melayu | Deepgram Nova-3 `ms` | ElevenLabs Multilingual v2 | Malay-capable voices |
| Mandarin | Deepgram Nova-3 `zh` | ElevenLabs Multilingual v2 | Mandarin-capable voices |

Each variant has its full system prompt and first message written natively (not translated) — including culturally appropriate filler words, honorifics (`Encik`/`Puan` for Malay), and natural phone conversation patterns.

**Technical changes required:**
- `stt.py`: Add `language` param to Deepgram WebSocket URL
- `tts.py`: Switch to `eleven_multilingual_v2` for non-English variants
- `caller.py`: Route `+60` numbers through Malaysian Twilio number
- `config.py`: Add `TWILIO_PHONE_NUMBER_MY` env var

### 3.4 PDPA Compliance Layer

New `compliance.py` module, checked before every outbound call:

| Check | Implementation |
|-------|---------------|
| DNC list | SQLite table of opted-out numbers, checked pre-call |
| Call hours | Block calls before 9 AM / after 9 PM MYT |
| Phone validation | Malaysian format `+60` verification |
| Consent status | Per-patient consent tracking |
| Data retention | Auto-purge transcripts after 90 days (PDPA data minimization) |
| Recording consent | Agent asks after identity confirmation on every call |

---

## 4. Competitive Position

### 4.1 Why No One Owns This Niche

The US patient recall market has 15+ funded startups (Luma, Klara, Weave, NexHealth, Phreesia, etc.) all fighting for the same EMR-integrated, SMS-based, HIPAA-compliant workflow. They have zero incentive or infrastructure to serve SEA:

- No WhatsApp integration (SMS-centric)
- No Malay/Mandarin language support
- No PDPA expertise (they're built for HIPAA)
- No Malaysian telephony (Twilio coverage exists, but no one's using it)
- No understanding of multi-brand chains with different brand voices

**Our defensibility compounds over time.** Every call generates training data for Malaysian healthcare conversations — accent patterns, code-switching (Manglish), medical terminology in local context. This data moat gets wider with every Bloom outlet onboarded.

### 4.2 Adjacent Competitors to Monitor

| Player | Threat Level | Why |
|--------|-------------|-----|
| Plato (SG) | Medium | Healthcare comms in SEA, but focused on chat/scheduling, not voice |
| Local WhatsApp marketing agencies | Low | Manual, no AI, no voice |
| Retell/Bland/Vapi entering SEA | Low-Medium | Generic platforms, no healthcare vertical, no local language | 
| Bloom building in-house | Low | They're a healthcare company, not a tech company |

### 4.3 AI Voice Agent Pricing Benchmarks

For context on our cost position:

| Platform | $/min | Notes |
|----------|-------|-------|
| Bland AI | $0.12-0.14 | API-only, no vertical specialization |
| Vapi | $0.13-0.25 | Middleware, requires engineering |
| Retell AI | $0.05-0.14 | Best latency, but generic |
| Synthflow | $0.08-0.19 | No-code, white-label |
| Amazon Connect | $0.018 | Raw infrastructure, no agent framework |
| **Our COGS** | **~$0.04** | Twilio + Deepgram + GPT-4o + ElevenLabs |

We're at the infrastructure layer, not buying from middleware. This gives us room to price competitively while maintaining 80%+ gross margins.

---

## 5. Unit Economics

### 5.1 Cost Per Call

| Component | Cost/min | Per 2-min call |
|-----------|----------|----------------|
| Twilio (MY outbound) | $0.018 | $0.036 |
| Deepgram Nova-3 | $0.005 | $0.010 |
| ElevenLabs Flash v2.5 | $0.008 | $0.016 |
| GPT-4o (est. ~800 tokens/min) | $0.005 | $0.010 |
| **Total COGS** | **~$0.036** | **~$0.072** |

Average call duration estimate: 1.5 min (reminders/recalls) to 3 min (surveys/follow-ups). Blended average: ~2 min.

### 5.2 Revenue Model

**Option A — Per-outlet subscription (recommended):**

| Tier | Monthly / outlet | Includes | Target |
|------|-----------------|----------|--------|
| Starter | RM 500 (~$115) | 500 calls/month, 1 language, 3 scenarios | Small clinics |
| Growth | RM 1,200 (~$275) | 2,000 calls/month, 2 languages, all scenarios | Mid-size |
| Enterprise | RM 2,500 (~$575) | Unlimited calls, 3 languages, all scenarios, custom brand voice | Chains |

**Bloom projection (Enterprise tier, 50 outlets):**

| Metric | Value |
|--------|-------|
| Monthly revenue | RM 125,000 (~$28,750) |
| Annual revenue | RM 1,500,000 (~$345,000) |
| Est. monthly calls | 50,000-100,000 |
| Est. COGS (at 75K calls × $0.07) | ~$5,250/month |
| **Gross margin** | **~82%** |

### 5.3 Bloom's ROI

Conservative estimate: treatment recall recovers 5% of overdue patients per month.

- 50 outlets × 200 overdue patients each = 10,000 recall targets
- 5% recovery = 500 rebooked appointments/month
- Average rebooking value: RM 400 (blended dental + aesthetics)
- **Revenue recovered: RM 200,000/month**
- **Our cost to Bloom: RM 125,000/month**
- **Net ROI to Bloom: RM 75,000/month profit + intangible patient retention value**

At scale, this pricing is trivially justified.

---

## 6. Execution Plan

### 6.1 Three-Week Sprint

| Week | Deliverable | Files |
|------|-------------|-------|
| 1 | 6 English healthcare agent JSONs, tested via `/test` browser route | `agents/*.json` |
| 1-2 | 6 Malay + 6 Mandarin variants (18 total) | `agents/*_ms.json`, `agents/*_zh.json` |
| 2 | Brand config system + `get_agent()` brand merging | `agents/brands/*.json`, `main.py` |
| 2 | STT language param + multilingual TTS + MY phone routing | `stt.py`, `tts.py`, `pipeline.py`, `web_session.py`, `caller.py`, `config.py` |
| 3 | PDPA compliance module + storage schema + DNC | `compliance.py`, `storage.py`, `caller.py` |
| 3 | Dashboard updates (brand selector, +60 default, patient variable fields) + end-to-end testing | `static/index.html`, `.env.example` |

**What's explicitly deferred:**
- Batch calling (CSV upload, concurrent calls, retry logic) — ships after Bloom validates core scenarios
- WhatsApp Business API integration — Phase 2 product
- EMR/clinic management system integration — requires Bloom's tech stack assessment

### 6.2 Pilot Structure

| Parameter | Value |
|-----------|-------|
| Pilot outlets | 2-3 (1 Cantiq, 1-2 Kheng) |
| Pilot duration | 4 weeks |
| Scenarios enabled | Treatment recall + appointment reminder (highest ROI) |
| Languages | English first, add Malay in week 2 |
| Success metric | >10% of lapsed patients rebooked via AI call |
| Kill metric | <3% rebook rate after 4 weeks |
| Call volume | Est. 500-1,000 calls/week across pilot outlets |

### 6.3 Verification Checklist

1. **Browser test:** Each scenario via `/test` — verify tone, compliance sections, no medical advice leakage
2. **Brand test:** Calls with different `brand_id` values — verify tone injection and variable merging
3. **Compliance test:** Opted-out number (blocked), outside 9 AM-9 PM MYT (blocked)
4. **Trilingual test:** Each language variant with native speaker evaluation
5. **Live call test:** Real Twilio call to `+60` number — caller ID, audio quality, Malaysian English STT accuracy

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Malaysian English STT accuracy** — Deepgram may struggle with code-switching (Manglish) and local accents | Medium | High | Test extensively during pilot; fall back to Deepgram `multi` (auto-detect) if single-language accuracy is poor; evaluate Whisper as backup |
| **Single-client concentration** — Bloom is 100% of revenue initially | High | High | By design for first 6 months; begin pipeline development for Q&M Dental and other chains by month 3 |
| **Bloom's patient data sharing** — Requires trust + data processing agreement | Medium | High | Draft DPA before pilot; minimize data retention (90-day purge); offer on-premise deployment option if needed |
| **ElevenLabs Malay/Mandarin quality** — Multilingual v2 may produce unnatural prosody | Medium | Medium | Evaluate alternative TTS (Azure Neural, Google Cloud) for non-English; voice quality is testable pre-launch |
| **Regulatory change** — PDPA amendments or new AI disclosure requirements | Low | Medium | Built compliance as a module, not hardcoded; monitor Malaysian regulatory developments monthly |
| **Patient backlash to AI calls** — "Why is a robot calling me?" | Medium | Medium | Agent prompts never claim to be human; warm, natural tone; instant opt-out; frame as "calling on behalf of [clinic]" |
| **Twilio Malaysia reliability** — Call quality and delivery rates for +60 | Low | High | Test call completion rates during pilot; have Vonage/Bandwidth as fallback carriers |

---

## 8. Decision Framework

### 8.1 Why This Pivot, Why Now

| Factor | BPO/UTS Path | Healthcare/Bloom Path |
|--------|-------------|----------------------|
| Sales cycle | 12-18 months | Weeks (direct relationship) |
| Competition | Intense (NICE, Genesys, Retell, Synthflow) | None in SEA |
| Revenue model | Per-seat SaaS (misaligned with BPO economics) | Per-outcome (aligned with clinic revenue recovery) |
| Technical lift | Major (copilot, QA scoring, dialer integration) | Minimal (new JSON configs + compliance layer) |
| Time to revenue | 6-12 months | 4-6 weeks |
| Defensibility | Low (features, not data moat) | High (local language data, clinic relationships, regulatory know-how) |

### 8.2 What Success Looks Like

| Timeframe | Target |
|-----------|--------|
| Week 3 | All 18 agent scenarios built and browser-tested |
| Week 7 | Pilot live at 2-3 Bloom outlets with measurable rebook rates |
| Month 3 | Full Bloom rollout (50+ outlets), $25K+ MRR |
| Month 6 | Second healthcare chain signed, $50K+ MRR |
| Month 12 | WhatsApp channel live, 5+ clients, $150K+ MRR |

### 8.3 Kill Conditions

Abandon this direction if any of the following hold true after the pilot:
- Rebook rate from AI calls < 3% after tuning
- Bloom declines to expand past pilot outlets after 4 weeks
- STT accuracy for Malaysian English is fundamentally insufficient (<80% word accuracy) and no alternative STT fixes it
- PDPA or BNM regulatory guidance explicitly prohibits AI-initiated patient outreach

### 8.4 What We're NOT Doing

- **Not pursuing BPO/UTS.** Valuable market intelligence, wrong entry point for us.
- **Not building a generic voice AI platform.** Synthflow, Retell, and Vapi own that layer. We're vertical.
- **Not competing in the US.** Red ocean for patient recall; HIPAA compliance is a 6-month project alone.
- **Not replacing clinic staff.** AI handles the dial-out and initial conversation; human staff handles scheduling, medical questions, and complex interactions.

---

## Appendix A: BPO Competitive Landscape (Condensed)

This analysis was conducted evaluating UTS (Malaysia, 1,225 agents, RM 93M revenue) as a potential client. Retained here for market context.

### AI Voice Agent Startups

**Retell AI** — Most capital-efficient ($5.1M raised, $7.2M revenue). ~600ms latency, OpenAI showcase partner. 10M+ min/month. SOC 2 Type II + HIPAA. $0.05-0.14/min.

**Synthflow** — Leading no-code platform ($30M Series A, Accel). 4.9/5 G2 across 999 reviews. 200+ integrations, white-label agency program. $0.08-0.19/min.

**Vapi** — "Twilio for AI agents" (~$28M funding, $8M ARR). Maximum configurability, requires deep engineering. $0.13-0.25/min.

**Bland AI** — Enterprise API ($65M Series B). Sub-1s latency claims but poor support reviews. $0.12-0.14/min.

### Enterprise CCaaS

**NICE CXone** — 22.2% market share, Gartner MQ Leader. Acquired Cognigy for $955M (Sep 2025). $2.2B+ cloud revenue.

**Genesys Cloud** — 19.7% share, $2.4B ARR growing 33% YoY. Pioneered Large Action Model for agentic AI (Feb 2026). Backed by Salesforce + ServiceNow.

**Amazon Connect** — Pure pay-per-use at $0.018/min. No seat licenses. 16M+ daily interactions. Three consecutive years as Gartner MQ Leader.

### Outbound Dialers

**Orum** — $250/user/month, AI trained on 1B+ sales calls, 4x connect rates. Proven BPO adoption.

**Nooks** — $5,000/user/year, best UI, up to 10 parallel lines. B2B SaaS focused.

### QA / Analytics

**Observe.AI** — Contact-center-specific LLM, 95%+ adoption across 350+ enterprise deployments. Scores 100% of calls vs. traditional 2-5% manual sample.

**CallMiner** — Forrester Wave Leader, 20+ years of conversational data. Enterprise pricing.

### Key Market Data Points

- AI contact center market: $2.5B (2024) → $7-13B by 2030-2034, 18-24% CAGR
- Voice AI agents specifically: projected $47.5B by 2034, 34.8% CAGR
- Only 34% of contact centers migrated to cloud — massive runway remains
- 95% of customer service leaders plan to retain human agents
- Industry reality check in 2025: marketed 70-80% efficiency gains, actual results ~25%

---

## Appendix B: UTS Strategic Context

**Company:** United Tele Service (HK: 6113), ~$20M revenue, 1,225 employees, 9 contact centers in KL.

**Business:** Outbound telemarketing for Malaysian banks and insurers — insurance, credit cards, loans, takaful.

**AI maturity:** Zero. Manual scripts, manual QA (2-5% sample), no digital channels.

**Recent signal:** Acquired by Microhash International (Singapore). Renamed holding company to "BitStrat Holdings" (June 2025) — signals tech-forward transformation.

**Why we passed:** Long enterprise sales cycle, BPO economics misaligned with AI pricing, crowded competitive field, regulatory complexity of financial product telemarketing (PIAM/LIAM/BNM). The engagement was valuable for market intelligence but the wrong entry vector for a startup moving fast.
