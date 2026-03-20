# Development Plan: AI Healthcare Communication Platform

## Context

We have two working systems — an **AI outbound caller** (Twilio + Deepgram + GPT-4o + ElevenLabs) and an **AI mystery shopper** (Retell + email + webchat + WhatsApp) — and four documents mapping the opportunity space across two markets: **Bloom Healthcare Group** (Malaysia, 50+ outlets, dental/aesthetic/GP/spa) and **Bloom Healthcare** (US, 109-provider home-based senior care). This plan consolidates those inputs into a single development roadmap.

---

## 1. Strategic Direction

### Primary market: Southeast Asia (Malaysia first)

The research is unambiguous. The US patient-recall market is a red ocean with seven funded incumbents (SolutionReach, Luma Health, Phreesia, Weave, Artera, Klara, Relatient). Southeast Asia has **zero AI outbound calling solutions for healthcare**. None of the US players support WhatsApp, Bahasa Malaysia, or SEA pricing norms.

The competitive set in Malaysia is:
- Manual WhatsApp by reception staff
- Basic SMS blast features in local CMS platforms
- Nothing else

### Entry strategy: mystery shop as door opener, AI caller as core product

Use the mystery shopper to **generate a free Communication Audit Report** for Bloom Healthcare Group's subsidiaries. This demonstrates value before asking for anything and surfaces the exact gaps the AI caller solves. Sell the outbound platform on documented evidence.

### Target account: Bloom Healthcare Group (Salcon Berhad)

Cantiq Clinic, Kheng Dental, and The Bloom Healthcare are **subsidiaries of one publicly-listed parent**. This is a single enterprise deal across 50+ outlets, not three separate pitches.

**Entry point → Kheng Dental** (13+ branches, 100K patients, single WhatsApp bottleneck, clearest recall ROI from 6-month dental cycles).

---

## 2. What Exists Today

| Component | Status | Key tech |
|-----------|--------|----------|
| **AI outbound caller** (`ai_caller/`) | Working — phone + browser voice | Twilio, Deepgram Nova-3, GPT-4o streaming, ElevenLabs Flash v2.5, smart turn detection, barge-in, phone-line FX |
| **Mystery shopper** (`mystery_shopper/`) | Working — multi-channel | Retell phone, SMTP/IMAP email, Playwright webchat, wacli WhatsApp |
| **Mission dashboard** (`app/`) | Working — mission UI | Retell, email, webchat, scoring, timeline |
| **Agent scenarios** | 4 generic scenarios | debt_reminder, appointment_confirm, satisfaction_survey, membership_renewal |

---

## 3. What Needs to Be Built

### Phase 1: Healthcare-ready AI caller (Weeks 1–3)

The outbound caller works but has no healthcare-specific capabilities. These changes make it sellable to Bloom.

**Agent configs for healthcare**
- New agent JSONs: `dental_recall.json`, `aesthetic_followup.json`, `appointment_reminder.json`, `post_treatment_checkup.json`
- System prompts tuned for Malaysian healthcare context (clinic names, treatment terminology, pricing in RM)
- Template variables for patient name, clinic branch, treatment type, appointment date/time, doctor name

**Multilingual support**
- Bahasa Malaysia and Mandarin voice IDs in agent configs (ElevenLabs has multilingual voices)
- System prompts that handle Malay-English code-switching naturally
- Language detection or explicit language setting per patient

**WhatsApp as primary channel**
- WhatsApp Business API integration (utility messages ~RM0.02/message)
- WhatsApp-first outreach with voice call as escalation for non-responsive patients
- Template messages for appointment reminders, recall nudges, post-treatment check-ins
- Two-way conversation handling (patient replies → AI responds)

**Consent and compliance (PDPA)**
- Opt-in/opt-out tracking per patient (consent date, channel preferences)
- Call recording disclosure at start of every call
- Do-not-call list enforcement
- Caller ID transparency (clinic name displayed)
- Business hours enforcement with Friday prayer time sensitivity
- Data residency: Malaysia/Singapore hosting

**Patient data model**
- Patient records: name, phone, email, language preference, consent status, last visit, next due date, treatment history
- CSV/Excel import for initial patient lists (clinics won't have APIs day one)
- Basic CRM: patient status tracking, interaction history, outcome logging

### Phase 2: Mystery shopper → Communication Audit (Weeks 2–4)

Adapt the existing mystery shopper into a healthcare-specific audit tool that generates the sales collateral.

**Healthcare audit scenarios**
- New scenarios: dental clinic inquiry, aesthetic consultation booking, after-hours test, follow-up request, pricing inquiry
- Score on: response time, information quality, language handling, booking ease, after-hours availability

**Audit report generator**
- Professional PDF/HTML report: "Communication Audit — [Clinic Name]"
- Metrics: time-to-first-response, channel availability, information completeness, after-hours coverage
- Gap analysis table (similar to the one in the compass research)
- Revenue impact estimates (no-show rates × average treatment value × patient volume)
- Comparison against industry benchmarks

**Multi-branch execution**
- Run audit across all branches of a chain in parallel
- Branch-level and aggregate scoring
- Identify worst-performing branches (highest ROI for intervention)

### Phase 3: Dashboard and analytics (Weeks 4–6)

**Clinic operator dashboard**
- Per-branch call/message volume, success rates, patient responses
- Recall conversion tracking (contacted → booked → attended)
- No-show reduction metrics over time
- Revenue recovered estimates
- Real-time transcript viewer for active calls

**Group-level dashboard (Bloom HQ)**
- Cross-brand, cross-branch aggregate view
- Bloom Rewards program activation through AI touchpoints
- Cross-brand referral tracking (dental patient → aesthetic upsell)

### Phase 4: CMS integration (Weeks 6–10)

**Malaysian CMS connectors**
- kumoDoc, Remedi, Docspe, MagSys, Germs CMS — start with whichever Bloom uses
- Bi-directional sync: pull patient lists + appointment schedules, push back confirmed/rescheduled appointments
- FHIR/HL7 support for larger health systems

**Automated campaign triggers**
- 6-month dental recall: auto-contact patients whose last scaling was 5+ months ago
- Aesthetic rebooking: Botox patients at 3-month mark, laser patients at 2-week mark
- Appointment reminder: 48h + 2h before scheduled visit
- No-show follow-up: contact within 1 hour of missed appointment
- Post-treatment check-in: 3 days after procedure

---

## 4. Technical Architecture

```
Patient ← WhatsApp/Voice → AI Platform → Clinic CMS/PMS
                                ├── WhatsApp Business API (primary)
                                ├── Twilio Voice (escalation)
                                ├── Deepgram STT
                                ├── GPT-4o (conversation)
                                ├── ElevenLabs TTS
                                ├── Campaign scheduler
                                ├── Consent manager
                                └── Analytics DB
```

**Infrastructure decisions:**
- Cloud: AWS Singapore or GCP asia-southeast1 (data residency)
- Database: PostgreSQL (upgrade from SQLite for production)
- Queue: Redis for campaign scheduling and rate limiting
- WhatsApp: Official Business API via Meta Cloud API or BSP (360dialog, Twilio)
- Hosting: containerized (Docker), auto-scaling for campaign bursts

---

## 5. Pricing (Malaysian market)

| Tier | Target | Price | Includes |
|------|--------|-------|----------|
| **Starter** | Solo clinic (1 location) | RM149/mo (~$35) | 500 AI calls + 1,000 WhatsApp messages, 1 language, basic recall |
| **Growth** | Small chain (2–5 locations) | RM249/mo per outlet (~$58) | 1,000 AI calls + 3,000 WhatsApp, 2 languages, recall + reminders |
| **Enterprise** | Group (6+ locations) | RM199/mo per outlet (~$46) | Unlimited, all languages, full omnichannel, cross-brand, dedicated support |

At RM199/mo × 50 outlets = **RM9,950/mo (~$2,300 USD)** from Bloom alone. Month-to-month, no lock-in.

---

## 6. US Market (Secondary, Later)

The US Bloom Healthcare (home-based senior care, CO/TX) represents a **separate, higher-ACV opportunity** with different requirements:

- HIPAA compliance (BAAs, encryption, audit trails, 6-year retention)
- TCPA consent management (prior express consent, 8am–9pm calling windows, opt-out handling)
- eClinicalWorks EHR integration (HL7/FHIR)
- Pricing at $3,000–$8,000/mo (10–40x the Malaysian per-outlet rate)
- English-only, no WhatsApp (SMS + voice)

**Do not pursue simultaneously.** The compliance surface area, integration requirements, and sales cycle are fundamentally different. The Malaysian deployment builds the core product; the US expansion leverages it with a compliance and integration layer on top.

---

## 7. Go-to-Market Timeline

| Week | Milestone |
|------|-----------|
| **1** | Mystery shop Kheng Dental (all 13 branches) and Cantiq (all 5 branches) |
| **2** | Generate Communication Audit Reports; build healthcare agent configs |
| **3** | Present audit to Bloom operations/IT contact; propose free 30-day pilot |
| **4** | WhatsApp Business API approved; dental recall + appointment reminder agents live |
| **5–8** | Pilot at 2–3 Kheng Dental branches (highest traffic); measure no-show reduction and recall conversion |
| **9** | Present pilot results to Bloom Group corporate; propose group rollout |
| **10–14** | Roll out across all Kheng Dental branches, then Cantiq |
| **15+** | Remaining Bloom brands (Aessence, MediPulih, Antara); begin second customer acquisition |

---

## 8. Success Metrics for Pilot

| Metric | Target |
|--------|--------|
| No-show reduction | ≥20% vs. baseline |
| 6-month recall conversion | ≥10% of lapsed patients rebook |
| Patient response rate (WhatsApp) | ≥60% |
| Patient response rate (voice) | ≥40% |
| Time-to-first-contact (after trigger) | <5 minutes |
| Patient satisfaction (post-call survey) | ≥4/5 |
| Cost per successful contact | <RM2 |

---

## 9. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| PDPA non-compliance | RM1M fine, reputation damage | Built-in consent management, legal review of scripts, call recording disclosure |
| Calls flagged as scam (MCMC) | Numbers blocked | Clinic name identification upfront, registered caller ID, business hours only |
| WhatsApp Business API rejection | Lose primary channel | Apply early, maintain quality rating, use BSP as backup |
| Bloom says no | No anchor customer | Audit report is free value regardless; use it to approach other chains |
| Malay/Mandarin voice quality | Poor patient experience | Test ElevenLabs multilingual voices extensively; fall back to English if quality insufficient |
| CMS integration complexity | Delayed automation | Start with CSV import; build CMS connectors based on what Bloom actually uses |
| Low patient pickup rate | Weak pilot results | WhatsApp-first (higher engagement than voice); optimize send times; A/B test message templates |
