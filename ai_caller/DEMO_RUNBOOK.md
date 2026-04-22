# UTS Demo — Presenter Runbook

**Date:** April demo window
**Duration target:** 22 minutes scripted, 20-min Q&A buffer after
**Primary audience:** Kenneth + 2 stakeholders (BD/Ops)
**Delivery mode:** Live, in-browser, screen-shared

This runbook is the only document the presenter needs on the day. Read it
before the call, have it open on a second screen during delivery.

---

## Pre-flight (T-60 min)

Block 60 minutes before the call for a full dress rehearsal. Non-negotiable.

### Environment

- [ ] `cd ai_caller && python3 main.py` — server on `:8000`, health endpoint returns all four green
- [ ] ngrok tunnel up (only if demoing the +60 Twilio leg; otherwise skip)
- [ ] `.env` has `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY` populated
- [ ] Synthetic fleet seeded: `python3 synth_data.py --count 100` (run the night before; takes ~8-12 min)
- [ ] Chrome with three tabs ready:
  - Tab A: `http://localhost:8000/demo` (launcher)
  - Tab B: `http://localhost:8000/qa` (fleet dashboard pre-loaded)
  - Tab C: terminal with `tail -f` on server logs (for diagnostics — do not screen-share this)
- [ ] Mic tested. Wear a headset — laptop mic will echo the agent's voice back into STT
- [ ] Close Slack, email, all notifications
- [ ] External monitor arranged so Kenneth sees Copilot and you drive caller

### Rehearsal

Run through Scenarios A–C exactly once end-to-end. Time yourself. Target:

- Scenario A: 4:30
- Scenario B: 6:30
- Scenario C: 4:30

If any scenario runs over time: cut the corresponding "extended color" line in the script below.

### Fallback assets (in `demo_fallbacks/`)

- `puan_aminah_hero.mp4` — pre-recorded hero call (full audio + transcript) in case live STT fails in Bahasa
- `copilot_screenshot_with_flag.png` — static image of the compliance flag firing, for the nuclear fallback
- `fleet_dashboard.png` — static PNG of the fleet view, for when the server is down

Have these open in an unshared window. If we fall back, say: *"We're showing
you a recording so latency doesn't distract from the narrative; the live system
behaves identically."* Do not apologise. Do not explain the failure.

---

## The 22-minute script

### 0:00 — Opening (90s)

> *"Thanks for making the time, Kenneth. What I'm going to show you in the
> next twenty-two minutes is one complete call — in Bahasa — going through our
> system. You'll see three things: the AI agent that makes the first-touch
> call; a live copilot that sits next to your human closer while they work;
> and auto-QA that scores every call. Same pipeline, three products."*
>
> *"Nothing you'll see is pre-recorded. Everything's running on my laptop,
> hitting the cloud LLM and ElevenLabs live. If something breaks I'll call
> it out."*

Click **/demo** tab. Leave the "Start Call" state visible.

---

### 1:30 — Scenario A · First-Touch AI (5 min)

**Setup** (15s):
> *"Scenario: MayFirst Bank wants to offer a balance transfer to existing
> cardholders. We're calling Puan Aminah. This is one outbound call, no
> handoff yet, in Bahasa."*

**Actions:**
1. Click **Start Call**
2. Open both tabs (caller + copilot) when the buttons appear. Drag Copilot to Kenneth's screen.
3. In caller tab: click the mic button. Wait for Nurul's opening in Bahasa.

**Nurul's first line:** *"Hello assalamualaikum, boleh saya cakap dengan Puan Aminah?"*

**You play Puan Aminah. Your responses, in order:**

| # | You say (Bahasa + natural code-switch) | Purpose |
|---|---|---|
| 1 | "Ye, saya Aminah" | Confirm identity, unblocks pitch |
| 2 | "Okay" (when agent asks recording consent) | Satisfy compliance flag → watch it turn green on Copilot |
| 3 | "Alamak... sekejap, saya tengah sibuk ni" | Trigger "busy" coaching card (amber) |
| 4 | "Okay... actually, how does it work?" | Trigger "positive intent" card (green) |
| 5 | Wait silently | Let Nurul emit `[TRANSFER_TO_HUMAN]` → banner appears in Copilot |

**Narration as Copilot fires events** (don't pause, narrate over Nurul):

- When recording-consent flag goes green: *"That's the PIAM recording-consent disclosure — our compliance engine just saw it happen and checked it off."*
- When "busy" card fires: *"Now watch — customer said she's busy. Copilot just gave the closer the exact reframe to use."*
- When transfer banner shows: *"And there — the AI qualified interest, stepped out, and handed the customer to a human. That's the whole first-touch flow."*

**Key message at end:** *"What you just saw is one scenario JSON file. Everything —
the voice, the language, the compliance pack, the coaching triggers — all
driven by configuration. A new vertical or brand means a new JSON, not a new
platform."*

**Cut if overtime:** skip step #3 (busy card). Go straight from consent to positive intent.

---

### 6:30 — Scenario B · Live Copilot (7 min)

**Setup** (20s):
> *"Now I'm the human closer. The AI just transferred me a warm lead. The
> Copilot you just saw stays on my screen the whole time. I'll show you the
> coaching first, then — and this is the critical one — I'll show you the
> compliance flag fire."*

Continue from the same call — don't create a new one. Puan Aminah is still on the line in the caller tab.

**You speak (role-playing the human closer) through the caller mic:**

| # | You say (as closer, deliberately code-switched) | Copilot should show |
|---|---|---|
| 1 | "Hi Puan, ni Edison from MayFirst. Thanks ya for your time. So the balance transfer plan — tiga point lima percent for twelve months. Best kan?" | Nothing yet |
| 2 | *(Puan Aminah says)* "Eh, tapi interest tinggi tak? I dengar credit card rate biasanya mahal." | "Too expensive" card fires (amber) |
| 3 | "Actually Puan, that's exactly the point — standard card rate is around eighteen percent. Ours is three point five. Big saving." | **← ORCHESTRATED MISS** — you just pitched the rate without disclosing it reverts. Compliance flag fires RED. |
| 4 | *(Paused — let Kenneth see the red flag)* | "Effective interest rate disclosure" → fired |
| 5 | "Ah — I should have added, after twelve months it reverts to the standard eighteen percent rate. Always disclose that." | Flag stays fired (violation logged for QA) |

**Narration over the red flag:**

> *"This is the moment that costs you in audits. I didn't disclose the
> effective rate when I pitched the promotional one. PIAM requires both.
> Copilot flagged it in red within two seconds. In a real shift this is where
> the closer sees it, corrects themselves, and the violation gets logged for
> the QA pass anyway."*

> *"Kenneth — right now your QA team listens to what, five percent of calls?
> This gets you to a hundred."*

End Scenario B by clicking **stop** on the caller mic.

**Cut if overtime:** skip the closer's recovery at step #5 — just let the flag stay red and narrate.

---

### 13:30 — Scenario C · Auto-QA (5 min)

**Setup** (10s):
> *"Call ended. Let me open the scorecard."*

**Actions:**
1. Copy the call_id from the caller tab URL.
2. Go to `/qa?call_id=<the id>` — scorecard should load within 15-25s (LLM analysis).

**What you should see:**
- Overall score around 60-75 (amber zone because of the compliance miss)
- Script adherence section: most beats green, one partial
- Compliance: "Effective interest rate disclosure" fired red with the quoted evidence
- Sentiment curve: mixed — starts neutral, dips on the "interest tinggi" turn, recovers
- Coaching recommendations: should call out the effective-rate miss and suggest always pairing promotional rate with revert disclosure

**Narration while it loads:**

> *"While this scores, a question: how long does your QA team spend listening
> to one call — 15, 20 minutes? This one just took... [wait for load] ...
> twenty-three seconds."*

**When it loads:**

> *"Every one of those numbers is backed by a specific moment in the
> transcript. The compliance flag quotes the exact sentence. The coaching
> recommendations are grounded, not generic. Your QA lead can still spot-check
> this in two minutes — but now they're doing it to ten calls, not one."*

**Then switch to Fleet tab** (click the Fleet Dashboard tab):

> *"And here's the same engine on a hundred calls from overnight. Agents
> ranked by performance — Aminah's your top, Marina's struggling. Outcome
> distribution is realistic. Top compliance violations are ranked — guess
> which one shows up most? Effective-rate disclosure."*

> *"Your ops lead, day one, knows who to coach and what to coach them on."*

**Cut if overtime:** skip the fleet tab. Stay on the scorecard. Fleet is dessert.

---

### 18:30 — Close and the ask (3 min)

> *"So that's the full picture. One AI pipeline, three products. You could
> buy any one of them standalone and it works. You buy all three and they
> stack — every First-Touch call feeds the Copilot, every Copilot interaction
> feeds QA, every QA learning feeds back into the agent prompts."*

> *"We built this on your BT scenario because you told us it's your bread and
> butter. The compliance pack is v0 — we'd co-develop v1 with your compliance
> team in week one of a pilot."*

> *"My proposal: two-week paid pilot. We stand this up on one agent pod, ten
> seats, your choice of product — probably start with Copilot. I run it
> alongside your current setup. End of week two we have numbers. Win or lose,
> you keep everything we build."*

**The ask, explicit:**

> *"What I need from you today is two things. One: can I come back in a week
> with a pilot proposal and pricing. Two: who on your side should we pair
> with on the compliance pack — because that's the long pole. Who owns that?"*

**Then stop talking.** Let Kenneth respond.

---

## Failure modes and recoveries

### Latency > 4s on Nurul's first reply

Say: *"Hang on — cold start on the LLM. This is normal for the first call;
subsequent calls are under a second."* Wait. Do not panic. Do not switch tabs.

### STT misses a Bahasa phrase

Repeat the phrase more slowly. If it misses twice, say: *"STT just dropped a
word — in production we'd fine-tune the acoustic model on your actual call
data; right now we're running the base multilingual model."* Move on.

### Compliance flag doesn't fire on the orchestrated miss

You forgot the exact trigger. Immediately say the missing phrase in a slightly
different wording: *"...and the rate — three point five — is very competitive."*
The regex is on "three point five" + "balance transfer". If still no fire:
skip Scenario B's compliance-miss demo and go straight to the sentiment/coaching
narration in Scenario C — the scorecard still captures the violation there.

### Server crashes or browser hangs

Switch to `demo_fallbacks/puan_aminah_hero.mp4`. Say: *"While we sort that
out, let me show you the hero call we recorded last week — same flow, same
compliance miss, same scorecard."* Continue narration over the video. Come
back to live for Scenario C if server recovers.

### Kenneth asks a question mid-scenario

Finish the sentence you're on, then answer. Don't try to multitask with Nurul
talking in the background. If the question will take >30s, pause the mic and
answer fully.

---

## The questions Kenneth will probably ask

Pre-loaded answers — see `docs/pilot_scope.md` for the commercial crib sheet. Keep the
printed 1-pager next to the runbook.

The five most likely:

1. **"How much does this cost per month?"** → Pilot is fixed-fee. Production: per-seat for Copilot, per-minute for AI calls, per-call for QA. Concrete numbers in the follow-up email.
2. **"Where does the data go?"** → Self-hosted option available. For pilot we can use a VPC in Singapore. No customer data leaves your region.
3. **"Who else uses this in Malaysia?"** → Honest answer: we're early. You'd be the reference customer. That's why the pilot is paid but discounted.
4. **"Can it integrate with our current CRM?"** → Yes — read-only via API or SFTP for call lists, webhook or CSV export for results. Zendesk, Salesforce, custom — all within scope.
5. **"What if the AI says something wrong?"** → Three answers: (a) hard boundaries in the prompt — can't close sales, can't quote terms. (b) Compliance engine blocks it in real time. (c) Full transcript retained for dispute resolution.

---

## Post-demo checklist (same day)

Within 2 hours of the call ending:

- [ ] Send follow-up email with: 2-paragraph summary, 4-slide PDF deck, pilot SoW draft (from `docs/developer_plan.md` §8 "Post-demo engineering actions" + `docs/plan.md` §9 for decision tree)
- [ ] Save call_id of the live demo call for reference
- [ ] Export the QA scorecard PDF for Kenneth as a "here's what the output looks like" attachment
- [ ] Log actual scenario timings vs. script (for next demo calibration)
- [ ] One-sentence debrief to yourself: what was the weakest beat, what will you change next time

---

## Appendix: Quick reference commands

```bash
# Start server
cd ai_caller && python3 main.py

# Seed 100-call synthetic fleet (run the night before)
python3 synth_data.py --count 100

# Smaller seed for rapid rehearsal
python3 synth_data.py --count 20

# Check health (expect 4 green)
curl http://localhost:8000/api/health

# Wipe data before fresh demo (DESTRUCTIVE)
rm data/calls.db  # will be recreated on server start
```
