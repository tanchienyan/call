# Rivorix × UTS Demo Plan — End of April 2026

**Audience:** Engineering team
**Meeting:** Kenneth Woo (Tech Head, UTS), ~2 weeks out
**Specific constraint from client:** Demo in Bahasa Malaysia
**Document owner:** CTO
**Version:** 2.0

---

## 0. Strategic context: why this demo, given the Bloom pivot

Our strategy doc commits to healthcare patient recall in SEA, with Bloom Healthcare as the beachhead. This demo is for a BPO in a segment we've consciously deprioritized. That tension needs addressing before we burn 30 person-days of team capacity on it.

**The reconciliation:** this demo is not a strategic U-turn. It's a conscious bet on the following proposition:

1. **~80% of what we build here transfers directly to Bloom.** Bahasa voice, Malay+English code-switching STT, compliance-rule architecture, streaming Copilot UI patterns, single-call QA engine — all Phase 1-3 infrastructure from the pivot plan. See §7 reusability audit.
2. **Kenneth Woo is a warm inbound relationship we don't throw away.** Even if UTS never converts, engineering credibility with a publicly listed HK-traded BPO is a reference we can use when selling into regional healthcare groups (IHH, Bangkok Dusit) who think about operations similarly to BPOs.
3. **BPOs remain optionality, not roadmap.** If Kenneth signs a paid pilot, we re-evaluate. If he doesn't, we've still built the multilingual + compliance substrate we need for Bloom anyway.

**Spending cap for this demo: 25 person-days across the team, hard ceiling.** The original 30-day estimate has no buffer and includes work we should skip if it forces trade-offs against Bloom delivery. If we hit day 25 and something's still broken, we cut that scenario — see §13.

**If by Monday of Week 1 we can't commit to this without delaying Bloom Week-1 deliverables, we ship a shorter demo (Scenario A + C only) and negotiate a 1-week slip with Kenneth.** This is the CTO's call, made on Monday after stack lock.

---

## 1. What this demo must prove

One thing only: that Rivorix is the only vendor that can run the full outbound lifecycle — **dial → talk → review** — in Bahasa Malaysia, on a Malaysian financial-product script, with PIAM/LIAM compliance awareness baked in.

The Hilton demo already proved "we can build voice agents." This demo must prove "we can build *for UTS*." If Kenneth walks away remembering one sentence, it should be: *"Regal doesn't speak Bahasa, Observe doesn't close the loop, nobody's shipping PIAM compliance — these guys are."*

### Success criteria (measurable, in priority order)

| # | Criterion | How we measure |
|---|-----------|----------------|
| 1 | Kenneth commits to a paid pilot scoping call within 10 business days | Meeting on calendar with at least one UTS decision-maker |
| 2 | Kenneth asks a pricing or integration question during the demo | CTO or CEO logs it within 5 min of meeting end |
| 3 | Kenneth answers ≥2 of 3 strategic questions we pre-sent (tool-picker, QA %, follow-up flow) | Captured in follow-up email or during demo |
| 4 | Demo runs end-to-end without visible failure on any of the 3 scenarios | All 3 scenarios complete; fallback video not used |
| 5 | Native Malay speaker in the room (ours, after) rates Bahasa voice "believable as a call center agent" | Post-demo 1–5 rating, target ≥4 |

**Pass:** criteria 1 + 2 + 4. **Stretch:** all five. **Fail:** miss criterion 1.

### Anti-goals

- Showing breadth ("look at all the scenarios we support")
- Showing the Hilton booking again
- Pitching the dialer pillar (deferred)
- Overclaiming on autonomous cold-calling
- Any slide deck longer than 3 slides

---

## 2. Narrative arc (15–20 mins total)

We structure the demo as one continuous story on a single fake prospect — *"Puan Aminah, a Maybank credit card holder being offered a balance-transfer top-up."* One persona, three moments:

1. **Minute 0–5 — First-Touch AI agent** makes the outbound call in Bahasa. Hits voicemail on attempt 1 (shows smart VM handling). On attempt 2, Aminah answers. The AI qualifies interest, captures consent for recording, warm-transfers to a human closer.
2. **Minute 5–12 — Copilot on human closer's screen.** The human (Edison or a teammate) picks up the transfer. Copilot shows live transcript, objection-handling cards, and — the money shot — a PIAM compliance flag firing when the human forgets a required disclosure.
3. **Minute 12–17 — 100% Auto-QA.** Call ends. Within 30 seconds, the scorecard appears: script adherence %, sentiment curve, compliance list, recommended coaching. Then we zoom out: "Here's what the same engine produced on 100 historical calls overnight."

Minutes 17–20: architecture slide, integration story, Q&A.

**Emotional beats to engineer:**
- Minute 3: Aminah picks up, Bahasa voice sounds real → Kenneth visibly reacts (this is the first "wait, what" moment)
- Minute 9: compliance flag fires in red → Kenneth leans in (this is the moat moment)
- Minute 14: fleet dashboard shows 100 scored calls → Kenneth sees the "always-on" value (this is the pricing moment)

If we miss any of these three reactions, the demo didn't land.

---

## 3. Demo scenarios — concrete build spec

### Scenario A — First-Touch voice agent (Bahasa)

**Script:** Credit-card balance-transfer offer. Realistic Malaysian bank-outbound scenario. Written by a Malay-speaking team member, reviewed against PIAM consumer-credit telemarketing conventions. Script lives at `demos/uts/puan_aminah_hero.json` once drafted.

**Flow branches to support:**
- Voicemail → leaves short Bahasa message with callback number, logs disposition
- Wrong number → polite Bahasa apology + disposition
- "Not a good time" → schedules callback, confirms in Bahasa
- Interested → captures consent-to-record phrase verbatim, warm-transfers to human
- Not interested → respects opt-out, updates DNC list

**Must demonstrate code-switching.** Malaysian retail speech mixes Malay and English constantly ("Puan, saya nak offer you satu plan yang..."). The prospect persona should do this mid-call and the agent must track.

**Voice:** Female, warm, clearly human-sounding. Test ElevenLabs Bahasa, Azure Speech (ms-MY), and Google Cloud TTS (ms-MY). Pick best. Budget 2 days for voice A/B; **decision locked by end of Week 1 Tuesday** — no re-opening after that.

**Latency targets:**
- Voice agent end-of-turn to reply start: <1.5s
- Voicemail detection decision: <3s from ring pickup

### Scenario B — Real-time Copilot

A web UI on a second laptop the human closer "logs into." Three panels:

- **Live transcript** (left) — diarized, time-stamped, Bahasa + English
- **Coaching cards** (center) — objection-handling snippets that surface when a trigger phrase is detected ("mahal," "kena fikir dulu," "tanya husband")
- **Compliance flags** (right) — a checklist that ticks off mandatory disclosures in real time; fires red alert if closer misses one

**The orchestrated miss:** the human deliberately forgets to state the interest rate disclosure. Copilot catches it, red banner appears, closer recovers on-call. This is the emotional peak of the demo — make sure it lands.

**De-risking the orchestrated miss:**
- The "human" closer is one of us, scripted. Rehearsed at least 5× in dry runs.
- Backup: if Copilot fails to fire the flag live, the presenter pauses, says "let me show you what this looks like on a past call," and cuts to a pre-recorded 15-second clip of the flag firing. Never let the demo stall waiting.

**Latency budget:** <2s from utterance to coaching card. Anything slower breaks the spell. Measured in dry run with actual clock.

### Scenario C — Auto-QA

Two views:

- **Single-call scorecard** for the call that just ended. PDF-style output showing: script adherence (%), compliance violations (list with timestamps), sentiment curve, recommended coaching points, agent performance score.
- **Fleet dashboard** showing the same engine applied to 100 historical calls (synthetic, but labeled plausibly — "UTS-Sample-Campaign-2026-04"). Tiles: agents ranked by performance, top missed objections, top compliance risks, cross-sell opportunities detected but not taken.

The fleet view is where we earn the "100% QA" claim — sampling-based QA can't produce this.

**Scorecard generation latency:** <30s from call end. If it's slower, we show a pre-generated version and lie about when it was made. This is fine — the real product will get there; the demo is about the UX, not the async job.

---

## 4. What we're explicitly NOT showing

- **No autonomous cold-calling of real numbers.** TCPA-equivalent risk, and Kenneth will know. Keep First-Touch framed as "works on warm or opted-in lists, qualifies before human picks up."
- **No dialer pillar.** We integrate with their existing dialer; we don't replace it. If Kenneth asks, our answer is "we plug in on top of Genesys/Avaya/whatever you run — we're not here to rip-and-replace."
- **No WhatsApp follow-up pillar.** Mention it as Phase 2 roadmap only. This demo is already full.
- **No pricing slide.** Verbal answer when asked: "Per-seat for Copilot at $75-100 range, per-minute for QA at $0.02-0.05 range, happy to scope exact numbers once we understand your client contracts and volumes." **Nobody says specific numbers outside this range.** Rehearsed.

### Commercial posture crib sheet (rehearse these answers)

| Question | Answer (memorize, <30s) |
|----------|-------------------------|
| "How much?" | See pricing range above. Defer exact to scoping call. |
| "When can we pilot?" | "30-day pilot, Copilot + QA on one campaign, can start within 3 weeks of kickoff." |
| "On-prem?" | "VPC deployment yes, air-gapped on-prem is Phase 2 — happy to scope if it's a blocker." |
| "Integration with our dialer?" | "We tap the audio stream via SIPREC or Twilio — no changes to your dialer." |
| "Data security / where does audio live?" | "Customer-owned encryption keys, Malaysia-region storage, 90-day retention default, configurable." |
| "How is this different from Observe.AI?" | "Observe samples English calls; we do 100% of Bahasa+English code-switched calls, with PIAM rules built in." |
| "Do you have other BPO clients?" | Honest: "UTS is our lead BPO engagement. We're selecting partners who want to shape the product." |

---

## 5. Technical architecture & build list

```
                   ┌────────────────┐
  Outbound call    │  Voice Agent   │
  (SIP via Twilio) │  (Bahasa LLM   │──┐
                   │   + TTS/STT)   │  │
                   └────────┬───────┘  │
                            │ warm     │
                            │ transfer │
                   ┌────────▼───────┐  │
  Human closer ────│  Copilot UI    │  │  every
                   │  + streaming   │  │  call
                   │  transcription │  │
                   └────────┬───────┘  │
                            │          │
                   ┌────────▼──────────▼──┐
                   │  QA Engine            │
                   │  (batch + single-call)│
                   └───────────────────────┘
```

**Components to build/stand up:**

| # | Component | Status | Owner | Effort (low / high) | Risk |
|---|---|---|---|---|---|
| 1 | Bahasa voice agent (extend existing engine) | Extend | Voice team | 4 / 7d | **High** — current engine is English-only; code-switching is non-trivial |
| 2 | SIP/Twilio outbound with voicemail detection | Extend | Voice team | 2 / 4d | Medium — Twilio AMD is imperfect, may need custom heuristic |
| 3 | Warm-transfer mechanism (attended conference) | Build | Voice team | 2 / 4d | **High** — Twilio `<Dial><Conference>` with mid-call transfer is touchy |
| 4 | Streaming STT for Bahasa + code-switch | Integrate | ML | 3 / 5d | **High** — vendor quality is the gating factor |
| 5 | Copilot UI (React, 3-panel) | Build | Frontend | 4 / 5d | Low |
| 6 | Coaching-card trigger engine (LLM + rules) | Build | ML | 3 / 4d | Low |
| 7 | PIAM/LIAM compliance rule pack v0 | Build | ML + compliance | 3 / 5d | Medium — research depth determines credibility |
| 8 | Auto-QA scorecard generator (single call) | Build | ML | 3 / 4d | Low |
| 9 | Fleet dashboard UI | Build | Frontend | 3 / 4d | Low |
| 10 | 100 synthetic Bahasa call transcripts + scores | Generate | ML | 2 / 3d | Low — but must be reviewed by native speaker |
| 11 | Demo orchestration script + cue cards | Write | CTO + CEO | 1 / 2d | Low |

**Revised totals:** 30d low estimate → **47d high estimate**. The 30d figure assumed no spillover. Realistic plan: 3-4 devs × 10 working days = 30-40 dev-days capacity. **We're at capacity or over.** The §0 spending cap of 25 days forces us to deprioritize #10 (from 100→50 calls) or cut #9 fleet dashboard to a static mockup if we slip.

**Stack choices to lock on day 1** (non-negotiable after this):
- STT: Azure Speech (ms-MY) first choice; fallback Deepgram Nova if code-switching is poor. **Benchmark both with 10 real code-switched clips on Monday.**
- TTS: ElevenLabs multilingual first choice; fallback Azure Neural (ms-MY female)
- LLM: Claude Sonnet for real-time coaching + QA; GPT-4o-mini for low-latency trigger classification
- Telephony: Twilio Programmable Voice + SIP
- Frontend: Next.js + Tailwind, single repo for both Copilot and QA dashboard

---

## 6. Data & content we need

**From UTS (still pending — ask again this week):**
- 1 anonymized outbound call recording (already requested)
- Sample outbound script (any campaign, any client)

**We generate (assume UTS sends nothing):**
- 3 realistic Bahasa outbound scripts: credit card, personal loan, motor insurance renewal
- 100 synthetic call transcripts with varied outcomes (converted, objected, not-interested, VM, wrong number) — labeled with ground-truth QA scores so our scorecard has consistency
- 1 "hero" transcript used for the live demo call (Puan Aminah persona)

**Person writing the scripts must be Malay-native.** Non-negotiable. Machine-translated Bahasa will be spotted in 10 seconds by Kenneth and kill credibility. **If we don't have this person on-team by Monday, we hire a contractor — budgeted $500-1,000, CEO approval.**

---

## 7. Reusability audit — what transfers to Bloom pivot

Critical for justifying the 25-day spend. Each row is an asset we keep regardless of UTS outcome.

| Asset built for UTS | Direct reuse for Bloom | Adaptation needed |
|---------------------|------------------------|-------------------|
| Bahasa voice agent (Scenario A) | Yes — all 6 Bloom scenarios need Bahasa variants | Just swap scenario JSON; voice, STT, TTS identical |
| Code-switching STT config (Malay+English) | Yes — Bloom patients code-switch too | None |
| Twilio warm-transfer mechanism | Partial — Bloom "transfer to clinic" use case | Minor rewire to clinic lines |
| Compliance rule pack architecture | **Huge** — PDPA for Bloom reuses the same rule engine, different rules | New Bloom rule pack (healthcare-specific), same code |
| Single-call scorecard generator | Yes — Bloom wants post-call summaries | Different scoring dimensions (not PIAM) |
| Fleet dashboard UI | Yes — Bloom chains want multi-outlet performance view | Rebrand, reorient metrics |
| Streaming transcript UI (Copilot) | Partial — Bloom clinic staff may want live assist during inbound calls | Deprioritize for now |
| Synthetic data generation pipeline | Yes — we need training/eval data for every new client | None |

**What's UTS-specific and won't reuse:**
- PIAM/LIAM rule content itself (but the engine that runs it, yes)
- Financial product vocabulary (credit, takaful, etc.)
- Script templates (financial outbound)

**Net:** roughly 80% of the ~25 dev-days are capex against the Bloom pivot, not opex for UTS. This is the CTO's core argument for proceeding.

---

## 8. Bahasa Malaysia localization — the quality bar

This is where we win or lose the meeting. Treat it as a separate workstream, not a checkbox.

- **Voice naturalness:** test with at least 3 native Malay speakers in the office before the demo. Not "it sounds okay," actually ask them "would you believe this is a call center agent."
- **Code-switching:** Malaysian outbound calls are not pure Bahasa. They're Bahasa-English hybrid with occasional Mandarin/Hokkien depending on region. The demo should include at least one natural code-switch to show the system handles it.
- **Honorifics and politeness registers:** "Puan/Encik" vs "you," "saya" vs "I" — get this wrong and it sounds condescending or wrong-register. Script reviewer must be from Malaysian customer-service background.
- **Financial vocabulary:** "faedah" (interest), "ansuran" (installment), "baki" (balance), "pengesahan" (verification). Mix of Malay financial terms and English product names is normal.

**Quality gate:** if the Week-2-Thursday native-speaker dry run returns a rating <4/5 on voice naturalness, we switch to a pre-recorded hero call for Scenario A. Hard rule, no arguing in the room.

---

## 9. PIAM/LIAM compliance pack v0

Researched deliverable, built once, reused across every Malaysian client forever. This is part of the moat.

**What to encode into the compliance rules:**
- Mandatory opening disclosure: agent identity, company name, purpose of call
- Consent-to-record capture language + explicit opt-in phrase
- Product disclosure requirements for credit products (effective interest rate, total repayment, fees)
- For insurance: product-summary disclosure, cooling-off period mention, no-pressure-tactics checklist
- Opt-out handling: mandatory acknowledgment within X seconds + DNC logging
- Call recording retention rules

**Source material:** Bank Negara Malaysia consumer protection guidelines, AKPK guidelines, PIAM and LIAM public materials. Circulars are not publicly available but enough is public to build a credible v0. Caveat the demo honestly: *"v0 rule pack built from public BNM + PIAM/LIAM sources; v1 co-developed with your compliance team."*

**Engine design note:** build the rule engine so the same framework runs Bloom's PDPA healthcare rules (Phase 4 of pivot plan) with a different rule JSON. No hardcoding of UTS-specific anything in the engine.

---

## 10. Two-week timeline

**Week 1 (Apr 21–27): Build in parallel**
- Mon — Stack lock (STT benchmark on 10 code-switched clips), script v1 drafted, voice A/B testing starts, contractor hired if needed
- Tue — Voice TTS locked (no re-opening), scenario JSON drafts, compliance rule research begins
- Wed–Thu — Copilot UI skeleton, QA engine prompt-tuned on synthetic data, warm-transfer wired end-to-end
- Fri — First end-to-end dry run (ugly but working); **checkpoint: if Scenario A isn't producing usable Bahasa by end of Friday, cut Scenario B+C scope to make room**
- Weekend: Bahasa voice polish, compliance rules pack v0 (optional, only if needed)

**Week 2 (Apr 28–May 4): Integration, polish, rehearsals**
- Mon — Full integration: Voice → Copilot → QA on one story
- Tue — Dry run #1 with CEO + CTO, capture every break
- Wed — Bug fix + polish. **Hard cut point:** anything still broken gets cut from the demo.
- Thu — Dry run #2 with native Malay speaker in the room, capture every awkward phrase
- Fri — Final dry run + record fallback video
- Demo day: end of week 2

**Hard rule:** if by Wednesday of week 2 anything is still broken, cut it. A 2-scenario demo that works beats a 3-scenario demo that stutters.

---

## 11. Rehearsals

Three dry runs, minimum:

1. **Technical dry run** — just the team, validating every technical path (voicemail, transfer, compliance flag, QA scorecard generation) fires reliably. Record latency metrics.
2. **Language dry run** — with a native Malay speaker who has never seen the product, capturing every awkward translation or wrong register. Target rating ≥4/5.
3. **Buyer dry run** — simulate Kenneth's likely questions (architecture, latency, security, on-prem, cost, integration) and time-box answers to <90s each. CEO plays Kenneth.

Record the final dry run end-to-end. This becomes the fallback video if anything fails live.

---

## 12. Risk register

Separate from fallbacks (§13). These are the things that could fail before demo day.

| # | Risk | Prob | Impact | Mitigation |
|---|------|------|--------|------------|
| 1 | Bahasa TTS quality insufficient across all 3 vendors | Low | High | 2-day A/B window; fallback to voice clone of native speaker |
| 2 | Code-switching STT accuracy <80% | Medium | High | Test Monday with 10 real clips; if poor, script Scenario A to minimize code-switch |
| 3 | Warm-transfer mechanism flaky (Twilio conference edge cases) | Medium | High | Pre-record the transfer moment as backup audio; cut attended-transfer to blind-transfer if needed |
| 4 | Orchestrated compliance miss fails to fire live | Medium | **Highest** (peak moment) | Rehearse 5×; pre-rendered 15s clip as backup; presenter scripted to transition cleanly |
| 5 | Kenneth brings a bank client rep unannounced | Low | Medium | CEO handles audience read; we have a "board-friendly" framing ready |
| 6 | Native-speaker reviewer not hired in time | Medium | High | CEO decision Monday; budget $1K cap for contractor |
| 7 | UTS sends a real call recording late, and ours sounds worse | Medium | Medium | Frame upfront: "ours is synthetic, send us real data and we'll redo in 48h" |
| 8 | Team capacity exceeded; Bloom Week-1 deliverables slip | Medium | **High** | §0 spending cap enforced; cut scenarios before cutting into Bloom |
| 9 | Latency on Copilot coaching cards >2s in real network conditions | Medium | Medium | Test on hotel wifi / mobile hotspot; pre-warm all models; edge caching |
| 10 | Kenneth is quiet, hard to read in the room | Medium | Medium | CEO is trained to ask "what questions does this raise?" at each scene transition |

---

## 13. Fallback plans

- **Internet dies:** fallback video of the full flow, narrated live
- **Live call audio drops:** pre-recorded audio file, play through Copilot as if live — Copilot still runs in real time
- **Bahasa voice sounds off on the day:** switch to pre-recorded "Puan Aminah's incoming call" audio file and demo the Copilot + QA flow on that
- **QA engine latency spikes:** pre-computed scorecard for the hero call, shown as if just generated
- **Warm-transfer fails mid-call:** presenter pivots — "in production this is a one-click transfer; let me show you what happens on the closer's screen" — cut to pre-staged Copilot session
- **Compliance flag doesn't fire:** presenter says "let me show you what this looks like when it does," cuts to recorded clip
- **Kenneth doesn't send a recording:** demo on our synthetic data, openly framed as "this is our data; send us yours and we'll show you the same on real UTS calls within 48 hours"

Every component has a pre-rendered artifact sitting on disk as insurance. **Owner of the fallback-artifacts folder: Frontend lead. Audited Thursday of Week 2.**

---

## 14. Day-of-demo logistics

**On our side in the room:**
- CEO — runs the meeting, reads Kenneth, handles commercial questions
- CTO — drives the demo, narrates the story, handles technical questions
- One engineer on standby (remote OK) for live debugging if needed

**On the other side (expected):**
- Kenneth Woo + likely 1-2 technical team members
- Possibly someone commercial — CEO ready for that

**Equipment:**
- Two laptops: primary (runs voice agent + Copilot), secondary (runs QA dashboard, acts as fallback)
- Mobile hotspot as backup internet (tested Thursday)
- USB audio interface for the hero call (not laptop mic)
- Printed 1-page architecture diagram × 3 copies
- No projector dependency — run on their screen share if possible, our laptop if not

**90-min session structure:**
- 0–5: CEO intro, what we're showing today
- 5–25: live demo (§2)
- 25–55: Q&A, architecture, integration discussion
- 55–75: next-steps conversation (pilot scoping)
- 75–90: buffer / wrap

---

## 15. Live observation plan

During the demo, one of us is always watching Kenneth, not the screen.

**Signals to log in real time (CEO, on a notepad):**
- Does he lean in at the Bahasa voice moment? (Y/N)
- Does he react to the compliance flag firing? (Y/N + verbatim quote if any)
- Does he interrupt with a question during Scenario C? (Y/N)
- Does he write anything down? (Y/N)
- Does he look at his phone during the demo? (Y/N — disengagement signal)

**Post-demo 30-min retro (same day):**
- What landed? What didn't?
- What question did he ask that we weren't ready for?
- Is he a buyer, a tourist, or a competitor in disguise?
- What's the probability of a paid pilot within 60 days? (CEO + CTO each give a number)

This retro happens before anyone goes home. Written notes in Notion.

---

## 16. Post-demo decision tree

What we do in the 48 hours after the demo depends entirely on which outcome fires.

### Outcome A — Strong interest (criteria 1+2+4 hit, stretch hit)

- Send pilot scope proposal within 24h (drafted in advance — see §17)
- Schedule scoping call within 10 business days
- Hold Bloom Week-3 scope firm — don't over-rotate toward UTS
- Start drafting data processing agreement + security questionnaire answers

### Outcome B — Soft yes / "impressed but..." (criterion 4 hits, 1 + 2 partial)

- Send architecture diagram + compliance coverage map within 24h
- Offer a reduced-scope pilot (Copilot only, no QA) to lower his activation energy
- Follow up in 7 days with a specific ask (send us one recording, we'll show you QA)
- **Do not** chase more than 2× in 30 days

### Outcome C — Polite no / "interesting, we'll be in touch"

- Send thank-you + 1-page summary within 24h
- Log learnings in Notion, specifically: what feature did he implicitly ask for that we don't have?
- No further outreach for 90 days
- Feed learnings into Bloom product scoping
- Consider whether the BPO ICP is killable or if another BPO beachhead exists (UTS isn't representative)

### Outcome D — Technical failure on demo day (criterion 4 miss)

- Honest email same day: "technical issue on X; here's the recording of the working version"
- Offer re-demo within 10 days (virtual)
- CTO post-mortem within 48h on what broke and why rehearsals didn't catch it

**Draft all four follow-up emails before demo day.** Load them into drafts folder. The post-demo moment is about speed, not thinking.

---

## 17. Post-demo assets (prep during week 2)

Within 24 hours of the demo, Kenneth gets (assembled and ready Thursday of Week 2):

- 1-page architecture diagram (PDF)
- 1-page PIAM/LIAM compliance coverage map (PDF)
- Pilot scope proposal — Copilot + QA on one UTS campaign, 30 days, fixed-fee structure (range pre-approved by CEO), clear success metrics
- Link to the demo recording + QA output for one UTS call (if they've sent one by then)
- Security one-pager (data residency, encryption, retention, SOC 2 roadmap)

The proposal document is what converts the demo to revenue. **Draft it before the demo, not after.**

---

## 18. Decisions needed by Monday

Each requires a named owner and a Monday EOD deadline. No decisions = build stops.

| # | Decision | Owner | Deadline | Impact if late |
|---|----------|-------|----------|----------------|
| 1 | Who on the team is Malay-native and owns script + language QA? If nobody, hire a contractor. | CEO | Mon 5pm | Contractor hire slips → Bahasa quality risk |
| 2 | Budget approval: ElevenLabs enterprise Bahasa cloning ($X) vs Azure default voices ($0). | CEO | Mon 5pm | Voice quality ceiling set |
| 3 | Is the Hilton demo voice engine already Twilio-integrated, or do we wire SIP this week? | CTO | Mon 12pm | 2-day slip if we're wrong |
| 4 | Fleet dashboard: 100 calls or 500? (500 is more impressive, 5× more synthetic-data work.) | CTO | Mon 5pm | Scope creep risk |
| 5 | STT benchmark decision (Azure vs Deepgram) after 10-clip code-switch test | ML lead | Mon 5pm | Drives remaining 9 days of voice work |
| 6 | Is the CTO comfortable committing 25 person-days without delaying Bloom Week-1 scope? If no, we send Kenneth a 1-week slip request today. | CTO + CEO | Mon 12pm | Re-plan or re-scope |
| 7 | Which native Malay speaker attends Week-2-Thursday dry run? (Must be arranged by Monday.) | CEO | Mon 5pm | Language dry run blocks otherwise |

---

**Next deliverables from this document:**
1. The minute-by-minute orchestration script (presenter cue cards) — drafted after scenarios lock Week 1 Wed
2. Four pre-drafted post-demo follow-up emails (one per outcome in §16) — drafted Week 2 Thursday
3. The pilot scope proposal PDF — drafted Week 2, CEO-approved before demo day
