# Demo fallback assets

Capture these before demo day. Keep them in an **unshared** window. If the
live system fails, drop to the fallback without apologising and without
explaining the failure — see `../DEMO_RUNBOOK.md` §Failure modes.

## What to capture

| File | What it is | How to capture |
|---|---|---|
| `puan_aminah_hero.mp4` | Full 4-5 min Bahasa hero call (Scenario A end-to-end). Audio + screen capture of the caller + Copilot tabs side by side. | QuickTime (Cmd-Shift-5) of the two tabs. Run a clean rehearsal, keep the best take. |
| `copilot_screenshot_with_flag.png` | Full-window Copilot screenshot with the red `interest_rate_disclosure` flag fired + evidence text visible. | Trigger the orchestrated miss in Scenario B, then Cmd-Shift-4, window select. |
| `fleet_dashboard.png` | Full-window screenshot of `/qa` on the Fleet tab with at least 50 calls loaded. | Run `python3 synth_data.py --count 100`, open `/qa`, switch to Fleet tab, Cmd-Shift-4. |

## Rehearsal checklist

- [ ] Each MP4 fits in memory (Chrome's tab-switching quirks on 4K make 1080p
  the safe target — do not re-encode to save size).
- [ ] Screenshots are saved at native resolution (no browser zoom).
- [ ] All three files are in this directory before demo day (not in Downloads).
- [ ] Open them in Preview / QuickTime **before** the call so launch latency
  doesn't stall a live fallback.

## Never check these into git

The `.gitignore` at repo root covers `*.mp4` and large PNGs, but verify with
`git status` before commit. The videos contain recognisable audio of the
presenter; they are not suitable for a public repo.
