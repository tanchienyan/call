# Demo Fallback Artifacts — Slot Definitions

**Owner:** Frontend lead.
**Audit gate:** Wed 30 Apr 17:00 MYT (per `docs/developer_plan.md` §6).
**Sign-off:** this README. Tick each slot as it lands, sign at the bottom.

> **This directory is gitignored** (see root `.gitignore`). Artifacts ship via a pinned Dropbox/Drive folder — CTO to nominate path by Tue 22 Apr. Do not commit audio, video, or screenshots.

Every artifact here pairs to one row in `docs/plan.md` §8 (fallback and rehearsal plan). If a live demo component breaks, the presenter cuts to the matching artifact without missing a beat.

## Slots

### `full_demo_recording.mp4`
- **Purpose:** absolute fallback. Presenter narrates over the recording if the internet drops or the stack fully craters.
- **Produced during:** Dry run #3 (Wed 30 Apr), QuickTime screen capture.
- **Spec:** 1080p, 20 min, mic + system audio, cursor visible.
- **Status:** [ ] pending

### `hero_call_audio.wav`
- **Purpose:** Scenario A failure fallback. "Here's the same call from a different session."
- **Produced during:** Dry run #2 (Tue 29 Apr), capture via macOS screen recording with system audio enabled.
- **Spec:** 44.1 kHz WAV, mono, full call duration (~6 min).
- **Status:** [ ] pending

### `hero_scorecard.json`
- **Purpose:** QA engine latency fallback. Open directly in a tab: "here's what just ran."
- **Produced:** `python -c "from qa_engine import score_call; print(score_call(CALL_ID))"` with the dry-run #2 call_id, redirect to this file.
- **Spec:** must parse as JSON and conform to the current scorecard schema in `qa_engine.py`.
- **Status:** [ ] pending

### `compliance_flag_clip.mp4`
- **Purpose:** Scenario B fallback if the orchestrated compliance miss fails to fire.
- **Produced during:** Dry run #1 (Fri 25 Apr) — the run that hits Scenario B.
- **Spec:** 30 s QuickTime screen capture centered on Copilot right-hand panel, showing the flag flipping red.
- **Status:** [ ] pending

### `fleet_dashboard.png`
- **Purpose:** Scenario C fallback if `/qa` fails to load.
- **Produced:** macOS ⌘⇧4 region capture during dry run #2 after synthetic fleet is populated.
- **Spec:** PNG, full dashboard visible, today's real call pinned at top.
- **Status:** [ ] pending

### `pre_recorded_transfer.mp4`
- **Purpose:** warm-transfer fallback. "In production this is one click."
- **Produced during:** Scenario A recording in dry run #1, sliced at `[TRANSFER_TO_HUMAN]`.
- **Spec:** MP4, ≤60 s, starts from "I'd like to transfer you to my colleague."
- **Status:** [ ] pending

### `voice_ab/*.mp3`
- **Purpose:** voice A/B review trail. Not a demo fallback — keeps the T-6 audit evidence.
- **Produced during:** T-6 voice A/B test (Tue 22 Apr) — see `docs/developer_plan.md` §4 T-6 for exact generation script.
- **Files:** `jawid.mp3`, `valentine.mp3`, optional `pvc.mp3` if Creator tier chosen.
- **Status:** [ ] pending

---

## Sign-off

| Role | Name | Date | Notes |
|---|---|---|---|
| Frontend lead | | | All 6 demo-fallback slots filled, spec-matched |
| CTO | | | Verified via `docs/plan.md` §8 row-by-row |

If any slot is still empty at the sign-off gate, we cut the associated scenario per `docs/plan.md` §4 hard-cut rules.
