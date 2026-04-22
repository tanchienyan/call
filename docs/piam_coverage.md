# PIAM Consumer-Credit Rule Pack v0 — Coverage

**Pack ID:** `piam_consumer_credit_v0`
**Applies to:** Malaysian consumer credit telemarketing (credit card, balance transfer, personal loan)
**Built from:**
- BNM Policy Document on Fair Treatment of Financial Consumers (2019)
- BNM Guidelines on Credit Card (2011, updated)
- PIAM Code of Ethics & Conduct (public summary)

**Shipped with demo:** 10 rules. v1 co-developed with client compliance team in week 1 of pilot.

---

## Coverage matrix

| # | Rule | Detection | Severity | Languages | Live or post-call |
|---|------|-----------|----------|-----------|--------------------|
| 1 | **AI identity proactively disclosed** | First-N-turns regex (agent must say "AI assistant / pembantu AI / 智能助理" within first 2 turns) | Mandatory, High on miss | EN · BM · ZH | Live |
| 2 | **Agent + company identity disclosure** | LLM post-call audit (name + institution within first 30s) | Mandatory, High on miss | EN · BM · ZH | Post-call |
| 3 | **Call recording consent** | LLM post-call audit (consent before product discussion) | Mandatory, Critical on miss | EN · BM · ZH | Post-call |
| 4 | **Effective interest rate disclosure** | Regex trigger + regex fulfilment (promotional rate triggers must-contain "effective rate / standard rate / reverts to" within 3 turns) | Mandatory, Critical on miss | EN · BM | Live |
| 5 | **No pressure / urgency tactics** | Regex catch of 20+ trigger phrases | Mandatory, High on miss | EN · BM · ZH | Live |
| 6 | **Opt-out acknowledged** | LLM post-call audit (consumer decline → agent respects within 10s) | Mandatory, Critical on miss | EN · BM · ZH | Post-call |
| 7 | **No false affiliation or government claims** | Regex catch of protected terms with exception handling | Mandatory, Critical on miss | EN · BM | Live |
| 8 | **Third-party disclosure refusal** | LLM post-call audit (detect third-party answered + agent refusal) | Mandatory, Critical on miss | EN · BM · ZH | Post-call |
| 9 | **AI agent must not close sale** | LLM post-call audit (AI stayed in qualify-and-transfer scope) | Mandatory, Critical on miss, internal-audit only | EN · BM · ZH | Post-call |
| 10 | **Call purpose disclosed before product detail** | LLM post-call audit (purpose stated before specific terms) | Mandatory, High on miss | EN · BM · ZH | Post-call |

---

## What "live" vs "post-call" means

**Live (4 of 10):** fires in <100ms during the call, surfaces on the Copilot UI to the human agent, and flips the compliance checklist red. These are the rules where regex is the right primitive — they have unambiguous textual signatures.

**Post-call (6 of 10):** batched LLM audit the moment the call ends. Writes flag + verbatim evidence to the SQLite corpus and shows up on the scorecard. These are rules where context matters — e.g. "did the consumer opt out" needs understanding of intent, not just keywords.

---

## Trilingual support

Every regex-type rule carries triggers in the three languages UTS callers encounter:

- **English** — default
- **Bahasa Malaysia** — including code-switched phrases ("mahal lah", "kena fikir dulu", "hari ini sahaja")
- **Mandarin** — primarily for code-switched banking vocabulary ("今天截止", "名额有限")

LLM-type rules handle multilingual input natively via GPT-4o; no separate rule sets needed.

---

## The orchestrated miss (Scenario B demo)

**Rule 4 — Effective interest rate disclosure** is the rule the human closer deliberately misses in Scenario B. The closer quotes the 3.5% promotional rate without disclosing the 18% reversion rate. Copilot detects the trigger on turn 1, watches for the must-contain fulfilment over the next 3 turns, and flips red when the closer moves on without satisfying it. On the post-call scorecard, this registers as a Critical flag with verbatim evidence:

```
Trigger turn: "We can transfer at three point five percent for twelve months."
Missing disclosure: no mention of effective/standard rate, reversion, or post-promotional rate
Severity: critical
Evidence: turns 17–23
```

---

## What's NOT in v0 (explicit)

Shipped as v0 because these additions require your compliance team's interpretation:

- **Debt collection-specific rules** — different BNM policy document, different tone requirements.
- **Vulnerable-consumer handling** — requires your policy on age / disability / financial distress signals.
- **Cross-selling restrictions** — bank-specific internal policy.
- **Do Not Call registry integration** — requires your DNC data source.
- **Recording retention + PDPA purge** — requires your data governance spec.

v1 with your compliance team closes these gaps. 30-day pilot scope includes at least 3 of them.

---

## Evidence chain

Every flag event is recorded in the SQLite corpus with:

- `call_id` — primary key
- `rule_id` — which rule fired
- `turn_idx` — which turn triggered
- `evidence` — verbatim quote from transcript
- `severity` — at miss
- `audit_source` — `live_regex` / `post_call_llm` / `human_override`

Auditor can reconstruct any flag back to the exact quote. Chain of custody designed for regulator review.

---

## Engine details (for your technical reviewer)

- Pack is a single JSON file — editable by compliance, no code deploy required.
- Engine is rule-type-agnostic: `regex_any`, `first_n_turns_must_contain`, `llm`. New rule types added by extending `compliance.py`.
- Live evaluation: <10ms per turn per rule. Never blocks Copilot latency budget.
- Post-call audit: single GPT-4o call, ~2–4 seconds, batched across all LLM rules.

All code at `ai_caller/compliance.py` + pack file at `ai_caller/compliance/piam_consumer_credit_v0.json` — shipped in the pilot-engagement repo.

---

**For architecture, see the companion "Architecture" 1-pager. For pilot scope, see "Pilot Scope."**
