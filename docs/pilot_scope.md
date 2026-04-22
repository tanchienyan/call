# Pilot Scope — UTS × Rivorix

**Prepared for:** UTS Worldwide, Kenneth Woo
**Prepared by:** Rivorix (Edison Tan + team)
**Date:** 1 May 2026
**Status:** Proposal — to be refined in scoping call within 10 business days of demo.

---

## Executive summary

**30-day paid pilot**, one outbound campaign, one language (Bahasa Malaysia), 5 seats of live Copilot + 100% auto-QA on every call, integrated on top of your existing dialer.

**Price:** [TBD — CEO to fill per B-1.6 decision, single number, no line items].

**Scoping call target:** within 10 business days of today.

---

## Pilot objectives (we agree on these; you measure them)

1. **Voice quality:** ≥80% of UTS call-center managers rate the Bahasa AI agent "indistinguishable from a human agent" on blind A/B listening.
2. **Copilot coaching impact:** ≥20% reduction in objection-handling time per call (measured from first customer objection to resolution or transfer).
3. **Auto-QA coverage:** 100% of pilot calls auto-scored vs. your current 3–5% human sample; human-override rate <15% (measuring auto-QA trust).
4. **Compliance rate:** zero Critical-severity flags missed by Copilot in live audit (post-call human review).
5. **Transfer efficacy:** warm-transfer flow maintains ≥70% close rate on transferred leads (vs. your current AI-free baseline).

If we don't hit 3 of 5 at day 30, you walk away with no conversion obligation.

---

## What we ship

### Week 1 — Onboarding
- Compliance pack v1 co-developed with your team. PIAM v0 shipped with demo is the starting point.
- One campaign scenario adapted from your existing script (balance transfer, personal loan, or a campaign of your choosing).
- Voice A/B completed against 3 candidate voices; your managers pick the winner.
- Dialer / CCaaS integration — we ride on top; your existing flows unchanged.

### Week 2 — Shadow mode
- Copilot + Auto-QA run on your human agents' calls only. No AI outbound yet.
- You see the coaching cards firing live on your 5 pilot seats.
- You see 1 week's worth of 100%-coverage QA scorecards.
- Your compliance team reviews the flag trail and tunes the pack.

### Weeks 3–4 — Live AI outbound
- First-Touch AI agent runs a limited volume of calls (initial target: 50/day ramping to 300/day).
- Human closers take the warm transfers.
- Copilot + Auto-QA continue on every call (AI and human).
- Weekly review on the 5 objective targets above.

### Day 30 — Review
- Full metrics report against the 5 objectives.
- Go / extend / end decision. Clean exit option for you.

---

## What you commit to

- **Seat time:** 5 human agents for Copilot + QA workflow.
- **Compliance reviewer:** 3–5 hours in week 1 co-developing rule pack v1.
- **Integration access:** API access to your dialer and outbound queue system (or a mutually-agreed integration point).
- **Data policy:** PDPA-compliant data-sharing agreement, template provided; we sign your standard DPA.
- **Feedback cadence:** weekly 30-min review with a named operations lead on your side.

---

## What you don't commit to

- No dialer rip-and-replace.
- No CRM migration.
- No multi-year contract — the 30-day pilot has a clean exit.
- No data lock-in — your corpus exports to SQLite / CSV / JSON at any time, we keep nothing you can't take with you.

---

## Success → what happens next

If the pilot hits 3+ objectives, we offer a 90-day rolling engagement at pilot-to-production unit economics:

- **Copilot + Auto-QA** — per-seat subscription, volume tiers.
- **First-Touch AI outbound** — per-minute pricing, no-sale-no-fee structure available.
- **Compliance packs** — annual licensing per rule pack, first pack ships with pilot.

Pricing ranges TBD in follow-up conversations; not committing to a number before we understand volume.

---

## Risks and how we handle them

| Risk | Mitigation |
|---|---|
| Voice sounds machine-translated to your customers | Voice A/B with your managers in week 1; clean exit in week 2 if quality doesn't clear bar |
| Compliance pack misses a rule your regulator enforces | Co-developed with your team in week 1; we ship updates as fast as your compliance reviewer approves |
| Integration with your CCaaS takes longer than 5 days | Week 2 shadow mode gives us buffer; AI-outbound doesn't start until integration is clean |
| Your agents resist Copilot overlay | Opt-in in week 2; 5 named volunteers rather than forced rollout |
| Regulatory change mid-pilot | Rule packs are data, not code — hotfix turnaround <48h |

---

## Why this is a good first pilot for you

- **Low lock-in.** 30 days, clean exit, exports your data.
- **Ride-on-top integration.** Zero disruption to your existing dialer workflow.
- **Compliance co-ownership.** Your team signs off on the rule pack; you own the interpretation.
- **Fleet visibility from day 1.** 100% QA coverage on day 1, not "eventually."
- **Low opportunity cost.** 5 agents, not 50. If it doesn't work, the blast radius is 5 seats.

---

## Why this is a good first pilot for us

- **One well-defined scope.** One campaign, one language, five seats, five metrics.
- **Named success criteria.** No "we'll see how it goes" — 3 of 5 or we don't convert.
- **Your compliance team shapes v1.** The pack we ship after this pilot is better than anything we could build on our own.
- **A Malaysian BPO reference logo.** If we deliver, we earn the right to approach the rest of the BPO market with "ask Kenneth."

---

## What we need to hear from you in the scoping call

1. **Campaign choice** — balance transfer, personal loan, insurance cross-sell? (Cantiq Clinic pivot — different pack, same engine, different pilot.)
2. **Dialer / CCaaS specifics** — which provider, which APIs you can expose.
3. **Compliance reviewer availability** — 3–5h in week 1.
4. **Price range you've budgeted** — we bring a number to the scoping call; you tell us if it's a planet we're both on.
5. **Data residency constraints** — in-region or can we use US providers for STT/LLM?

---

## Timeline at a glance

```
Demo day (1 May) ───────────► [Kenneth decision window]
                                     │
                  ≤10 business days   ▼
                            Scoping call
                                     │
                             Day 0 of pilot
                                     ▼
        ┌──── Week 1 ────┬──── Week 2 ────┬──── Week 3 ────┬──── Week 4 ────┐
        │ Onboarding     │ Shadow mode    │ AI outbound    │ AI outbound    │
        │ Pack v1        │ Copilot on     │ 50 → 150/day   │ 150 → 300/day  │
        │ Voice A/B      │ human calls    │                │ Day 30 review  │
        └────────────────┴────────────────┴────────────────┴────────────────┘
```

---

## Signatories

| Role | Name | Signature | Date |
|---|---|---|---|
| Rivorix CEO | Edison Tan | | |
| UTS | Kenneth Woo | | |

---

**This proposal is the input to the scoping call, not the final contract. Final SoW produced within 5 business days of scoping call alignment.**
