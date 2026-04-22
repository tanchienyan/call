# Rivorix — Voice + Copilot + QA Architecture

**Prepared for:** UTS Worldwide (Kenneth Woo and team)
**Date:** 1 May 2026
**Contact:** Edison Tan — [CEO email]

---

## What it is, in one sentence

A self-hosted AI outbound voice pipeline with live human-in-the-loop coaching and 100% automated post-call QA — designed to sit *on top of* your existing dialer / CCaaS, not replace it.

---

## The three pillars

**1. First-Touch AI** — fully autonomous Bahasa Malaysia outbound agent that qualifies interest, disclosing AI identity proactively and handing over to a human closer on warm interest. Per-brand tone, per-call variable interpolation, no retraining per scenario — new campaigns are a JSON config file.

**2. Live Copilot** — human-agent overlay that streams the live transcript, surfaces coaching cards under 2 seconds after the customer says a trigger phrase (price, stall, objection), and flips compliance indicators red in real time when rules are breached. Works on both the AI's calls and your human agents' calls — same engine, same UI.

**3. Auto-QA + Fleet Dashboard** — every call gets an LLM-generated scorecard the moment it ends: outcome, compliance flags, tone, scripted-beat adherence, recommended coaching. Fleet view aggregates the metrics you currently pay QA analysts to compile manually on a 3–5% sample. Human reviewers can override call outcomes with one click.

---

## Reference architecture

```
Caller audio (Twilio or browser WebRTC)
        │
        ▼
┌──────────────────────────────────────────────┐
│  Deepgram Nova-3 STT  (en/ms/zh/multi)       │
│  Smart-Turn v3.2 (ONNX) end-of-turn detect   │
└──────────────┬───────────────────────────────┘
               │ transcript turn
               ▼
┌──────────────────────────────────────────────┐
│  GPT-4o agent (agent JSON defines behavior)  │──→ TTS (ElevenLabs Flash v2.5 / Multilingual v2)
└──────────────┬───────────────────────────────┘
               │ published to CopilotBus
               ▼
┌─────────────────────────┬───────────────────────────┐
│   Live Copilot UI       │   Compliance Engine       │
│   • transcript stream   │   • PIAM regex rules      │
│   • coaching cards      │   • first-N-turn rules    │
│   • live flag panel     │   • deferred LLM audit    │
└─────────────────────────┴───────────────┬───────────┘
                                          │ on call end
                                          ▼
                        ┌─────────────────────────────┐
                        │  QA Engine (LLM scorecard)  │
                        │  Per-call + fleet metrics   │
                        └─────────────────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────┐
                        │  SQLite corpus (labelled)   │
                        │  outcome · qa_score · flags │
                        │  brand · language · consent │
                        └─────────────────────────────┘
```

Every layer is rule-pack-agnostic. Swap `piam_consumer_credit_v0.json` for a different compliance pack and the same engine works; swap the agent JSON and the same pipeline runs a different scenario.

---

## Key design choices

| Choice | Reason |
|---|---|
| Self-hosted on Twilio + Deepgram + OpenAI + ElevenLabs | No vendor lock-in. Swap any one provider without touching the other three. Fallback paths possible for each. |
| Rule-pack-agnostic compliance engine | Banks, insurers, clinics each have different rule packs. We author the pack; the engine stays unchanged. |
| JSON-defined agents, no code deploys for new scenarios | Client compliance and ops teams can review and edit agent prompts directly. |
| Labelled SQLite corpus | Every call becomes structured training data. Outcomes, compliance flags, human overrides — all queryable. |
| Smart-Turn ML end-of-turn detection (not VAD) | Natural overlap, backchannels ("yeah", "mm-hm") don't cut off the customer mid-sentence. |
| Proactive AI disclosure, not post-hoc | First two agent turns include "I am an AI assistant / pembantu AI" — pre-empts deceptive-AI regulation and reduces complaints. |

---

## What it integrates with

We sit *on top of* — not in place of — your existing:

- **Dialer / CCaaS:** Genesys, Avaya, Five9, Twilio Flex. Outbound initiated or handed off via standard SIP/PSTN.
- **CRM:** any HTTP-reachable system. Call outcomes posted back via webhook.
- **QA workflow:** the auto-scorecard is additive — your human reviewers keep overriding and the data goes back to your existing reporting stack.
- **WhatsApp / email follow-up:** not in this demo, same engine will drive it when it ships.

**Not in scope for v1:** ripping out your dialer, replacing your CRM, or touching your agent payroll. This is a workflow augmentation, not a replacement.

---

## Compliance posture

PIAM consumer-credit rule pack v0 (9 rules, see companion PDF) is shipped with the demo. It was built from public BNM guidelines and PIAM conduct materials. **v1 is co-developed with your compliance team in week 1 of any paid pilot** — we're not pretending to know your internal interpretation of every edge case.

Every flag event (live and post-call LLM-audited) is recorded with verbatim evidence in the SQLite corpus. Auditable chain of custody from rule to call to reviewer.

---

## Security posture (summary)

- Calls transcribed and scored in-region where provider regions allow.
- API keys are client-specific; no cross-tenant data mixing.
- SQLite corpus is the single persistence layer; backups and retention configurable per tenant.
- Recording consent captured in-call and labeled on the corpus row.

Full SOC 2 / ISO 27001 roadmap separate document; we're happy to discuss the 6-month path if that's a buying gate.

---

## What Kenneth sees on demo day

- **10 min** — Scenario A: fully autonomous Bahasa outbound call, warm transfer to a human closer.
- **6 min** — Scenario B: the human closer takes over; Copilot flashes a red compliance flag in real time when the closer omits the effective-rate disclosure.
- **4 min** — Scenario C: the fleet dashboard after 100 simulated calls — outcomes, compliance rates, per-agent QA score.

Everything runs against UTS-themed data (credit-card balance transfer pitch, Bahasa-native voice, PIAM-aligned compliance pack). The UTS customisation is a day's work of JSON; the pipeline underneath is the permanent asset.

---

**For a pilot scope, see the companion "Pilot Scope" 1-pager.**
