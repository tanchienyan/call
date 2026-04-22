# mystery_shopper — Reference Implementation

> ⚠️ **REFERENCE IMPLEMENTATION ONLY.** This directory is retained for pattern reference — Retell agent prompt structure, the `scoring/engine.py` criteria schema, persona-based scenario config, and the channel abstraction (phone / WhatsApp / web / email).
>
> - **Not a Rivorix product.** Do not ship, deploy, or bundle into `ai_caller/`.
> - **Do not import from `ai_caller/` → `mystery_shopper/` at runtime.** If a pattern is worth reusing, port the distilled snippet to `docs/references/mystery_shopper_learnings.md`.
> - No new features, no dependency bumps, no refactors.
> - Excluded from CI, deploys, and shared infra.
> - **Quarterly review:** if untouched for 90 days, archive to a sibling repo.
>
> Source of truth for scope + rationale: `docs/plan.md` §3.2.

---

## What this was

The codebase that produced the **Hilton NYC booking demo** — the concept proof that got Rivorix into the UTS conversation. It runs multi-persona mystery-shopping calls against hospitality targets over phone / WhatsApp / web, scores transcripts against weighted criteria, and produces reports.

It is preserved as a working artifact because:

1. The Retell agent prompt structure for natural turn-taking informed `ai_caller/agents/*.json`.
2. The `list[dict]` criteria schema in `scoring/engine.py` is what `ai_caller/qa_engine.py` descends from.
3. The persona-based scenario configuration pattern ports cleanly to any outbound scenario with variable customer profiles.
4. The channel abstraction (`channels/phone.py`, `whatsapp.py`, `web_browser.py`, `phone_retell.py`) is the sketch for any future inbound or multi-channel return.

## What gets ported out

If you're reaching for something from here, **don't import it** — port the distilled pattern into `docs/references/mystery_shopper_learnings.md` and reference *that* from `ai_caller/`. Runtime coupling between this dir and `ai_caller/` is explicitly forbidden.

## Layout

```
mystery_shopper/
├── scenarios/hotel.py         # personas + scoring criteria (the reusable template)
├── scoring/engine.py          # list[dict] criteria scorecard engine
├── orchestrator/              # demo_journey, real_journey, journey orchestration
├── channels/                  # phone, whatsapp, web_browser, phone_retell (Retell SDK)
├── analytics/                 # sentiment, analyzer
├── reporting/report.py        # report generation
├── web.py                     # local web UI (historical)
├── cli.py                     # CLI entry point (historical)
└── config.py, models.py       # config + typed models
```

## History

- **2024–2025:** active development for hospitality mystery shopping.
- **Q1 2026:** pivot to AI-outbound-caller (`ai_caller/`). This dir moved to reference status.
- **Q2 2026 (current):** scoped as reference-only per `docs/plan.md` §3.2. No runtime reachability from the product codebase.

If you're the next owner of Rivorix and this dir has been untouched for 90+ days: archive to a sibling repo and remove from the monorepo. The distilled patterns in `docs/references/` remain.
