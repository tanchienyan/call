# Three Questions for Kenneth — UTS Demo Discovery

**Purpose:** answer the BPO-as-buyer thesis regardless of whether the demo converts.
**Ask:** in the demo meeting or the follow-up email, whichever lands naturally. Not buried in demo prep comms.
**Owner:** CEO. Answers captured in `docs/kenneth_answers.md` same day.
**Strategic frame:** `plan.md` §10 — these drive pivot/persist/walk more than demo quality does.

---

## 1. Tooling authority

> "When you add dialer / QA / agent-assist, is that UTS's call or your bank/insurer client's specification?"

**What we're listening for:** who *buys* the tool. If UTS's banking clients specify the stack, the sales motion is bank-direct, not BPO — different startup, different ICP, different GTM. `plan.md` §12 kill condition #1.

## 2. Current QA spend

> "Roughly what % of calls does UTS QA today — in-house or outsourced — and what's it costing?"

**What we're listening for:** the denominator. A 3–5% sampled-manual-QA regime is the industry default and means the Auto-QA pillar has an obvious 100%-coverage story with hard ROI. If they already QA ≥30% of calls (unlikely but possible for regulated banking), the economic wedge is thinner and the pitch shifts to compliance-assist over pure volume.

## 3. Follow-up workflow

> "When a prospect says 'send me details' on a call, what happens in the next 60 minutes?"

**What we're listening for:** whether the follow-up channel (WhatsApp, email, SMS) is owned by UTS or handed off to the bank. If UTS owns it, the natural next-quarter wedge is the same AI stack on the inbound/follow-up channel (WhatsApp-first patient recall has the same engine underneath — see `.cursor` workspace rule). If the bank owns it, we're back to bank-direct and kill condition #1 compounds.

---

## How to ask

These are three separate questions, not a questionnaire. Natural openers:

- Q1: after Scenario A when he asks about integration — "Before we go there, one thing that'd save me guessing…"
- Q2: during Scenario C when the fleet dashboard is on screen — "Curious — what's your current QA coverage looking like?"
- Q3: after pilot-scope discussion — "One more, so we scope follow-up right…"

If the demo goes sideways, Q1 and Q2 still go into the follow-up email (Outcome B/C/D drafts cover this).

## Decision logic (CEO + CTO same-day retro)

| Q1 answer | Q2 answer | Q3 answer | Move |
|---|---|---|---|
| "our call" | ≥15% spend | UTS owns | Full pilot pursuit. UTS is ICP. |
| "our call" | <5% spend | UTS owns | Pilot pursuit, lead with Auto-QA ROI. |
| "client spec" | any | any | `plan.md` §12 fires. Pivot to bank-direct or Bloom. |
| "mixed" | any | UTS owns | 30-day scope with one fintech-client introduction as pilot gate. |
| any | any | bank owns | Scope shrinks to outbound-only; re-test on 6-month horizon. |

Kenneth's answers land in `docs/kenneth_answers.md` with timestamp and verbatim quotes where we have them.
