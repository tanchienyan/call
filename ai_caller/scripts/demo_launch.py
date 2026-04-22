#!/usr/bin/env python3
"""Demo bootstrap — one command to get the UTS demo ready.

Checks the environment, probes the three providers we depend on, initializes
the SQLite DB, seeds a synthetic fleet if the dashboard would otherwise be
empty, launches the FastAPI server, and opens the /demo launcher in the
default browser.

Usage (from the ai_caller/ directory, with .venv activated):
    python scripts/demo_launch.py

Options:
    --skip-seed        don't check/generate synthetic fleet
    --seed-count N     number of synthetic calls to generate if seeding (default 100)
    --skip-probe       skip provider health probes (useful when you know they're down)
    --no-browser       don't auto-open /demo (useful for headless testing)
    --port N           override server port (default from config/env)

See `docs/developer_plan.md` §4 T-13 for acceptance criteria.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Resolve ai_caller/ as CWD regardless of where this script was invoked.
HERE = Path(__file__).resolve().parent
AI_CALLER = HERE.parent
os.chdir(AI_CALLER)
sys.path.insert(0, str(AI_CALLER))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(AI_CALLER / ".env", override=True)

import httpx  # noqa: E402

import config  # noqa: E402
import storage  # noqa: E402


# ─── Provider probes ────────────────────────────────────────────────────────


async def _probe(
    name: str, url: str, headers: dict, timeout: float = 3.0
) -> tuple[str, bool, str]:
    """Return (name, ok, detail)."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url, headers=headers)
            if r.status_code == 200:
                return name, True, f"HTTP {r.status_code}"
            body = r.text[:120].replace("\n", " ")
            return name, False, f"HTTP {r.status_code} — {body}"
    except Exception as e:
        return name, False, f"{type(e).__name__}: {e}"


async def probe_providers() -> list[tuple[str, bool, str]]:
    """Probe OpenAI + Deepgram + ElevenLabs. Twilio is optional (no cheap probe)."""
    tasks = []
    if config.OPENAI_API_KEY:
        tasks.append(
            _probe(
                "openai",
                "https://api.openai.com/v1/models",
                {"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            )
        )
    else:
        tasks.append(_noop("openai", "missing OPENAI_API_KEY"))

    if config.DEEPGRAM_API_KEY:
        tasks.append(
            _probe(
                "deepgram",
                "https://api.deepgram.com/v1/projects",
                {"Authorization": f"Token {config.DEEPGRAM_API_KEY}"},
            )
        )
    else:
        tasks.append(_noop("deepgram", "missing DEEPGRAM_API_KEY"))

    if config.ELEVENLABS_API_KEY:
        tasks.append(
            _probe(
                "elevenlabs",
                "https://api.elevenlabs.io/v1/voices",
                {"xi-api-key": config.ELEVENLABS_API_KEY},
            )
        )
    else:
        tasks.append(_noop("elevenlabs", "missing ELEVENLABS_API_KEY"))

    return await asyncio.gather(*tasks)


async def _noop(name: str, detail: str) -> tuple[str, bool, str]:
    return name, False, detail


# ─── Synthetic fleet seeding ────────────────────────────────────────────────


def count_synthetic_calls() -> int:
    """How many synthetic calls are currently in the DB?"""
    import sqlite3

    storage.init_db()
    with sqlite3.connect(str(storage.DB_PATH)) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM calls WHERE is_synthetic = 1"
        ).fetchone()
    return row[0] if row else 0


async def seed_fleet(count: int) -> None:
    from synth_data import generate_fleet  # noqa: E402 — lazy import

    await generate_fleet(count, parallelism=5)


# ─── Server launch ──────────────────────────────────────────────────────────


def start_server(port: int) -> subprocess.Popen:
    """Launch main.py as a subprocess so this script can exit cleanly later."""
    env = dict(os.environ)
    env["PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(AI_CALLER),
        env=env,
        stdout=subprocess.DEVNULL,  # uvicorn is chatty; user can run main.py directly for logs
        stderr=subprocess.STDOUT,
    )
    return proc


async def wait_for_server(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=1.0) as c:
        while time.monotonic() < deadline:
            try:
                r = await c.get(f"http://localhost:{port}/api/health")
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.3)
    return False


# ─── Main orchestrator ──────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UTS demo bootstrap")
    p.add_argument("--skip-seed", action="store_true")
    p.add_argument("--seed-count", type=int, default=100)
    p.add_argument("--skip-probe", action="store_true")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", str(getattr(config, "PORT", 8000)))),
    )
    return p.parse_args()


def _style(ok: bool) -> str:
    return "\033[92m✓\033[0m" if ok else "\033[91m✗\033[0m"


async def _amain() -> int:
    args = parse_args()

    print("─── UTS Demo Bootstrap ───────────────────────────────────────")
    print(f"  ai_caller root : {AI_CALLER}")
    print(f"  python         : {sys.version.split()[0]}")
    print(f"  port           : {args.port}")
    print()

    # 1. Provider probes
    if args.skip_probe:
        print("  [skip] provider probes")
    else:
        print("  [1/4] probing providers…")
        results = await probe_providers()
        for name, ok, detail in results:
            print(f"        {_style(ok)} {name:<12} {detail}")
        core = {r[0]: r[1] for r in results}
        core_ok = core.get("openai") and core.get("deepgram") and core.get("elevenlabs")
        if not core_ok:
            print()
            print("  ⚠  One or more core providers are not authenticating.")
            print("     The server will still boot but calls will fail at runtime.")
            print("     See docs/developer_plan.md §3 Blocker B-2 for the fix path.")
            print()

    # 2. DB init
    print("  [2/4] initialising SQLite schema…")
    storage.init_db()
    synth_count = count_synthetic_calls()
    print(f"        {_style(True)} {synth_count} synthetic call(s) already in DB")

    # 3. Seed fleet if empty
    if args.skip_seed:
        print("  [3/4] [skip] synthetic seeding")
    elif synth_count >= 50:
        print(
            f"  [3/4] [skip] fleet already seeded ({synth_count} ≥ 50 threshold)"
        )
    else:
        need = max(args.seed_count - synth_count, 0)
        print(
            f"  [3/4] seeding fleet — generating {need} synthetic call(s)…"
        )
        print(
            "        (each call hits OpenAI twice — transcript + scorecard. "
            "Expect ~$0.01–0.05 per call.)"
        )
        try:
            await seed_fleet(need)
        except Exception as e:
            print(f"        {_style(False)} seed failed: {e}")
            print(
                "        (continuing — you can retry with "
                "`python synth_data.py --count N`)"
            )

    # 4. Start server + open browser
    print(f"  [4/4] starting server on :{args.port}…")
    proc = start_server(args.port)
    ok = await wait_for_server(args.port)
    if not ok:
        print(f"        {_style(False)} server did not come up in 15s")
        proc.kill()
        return 1
    print(f"        {_style(True)} server up at http://localhost:{args.port}/")

    print()
    url = f"http://localhost:{args.port}/demo"
    print(f"  ► Demo launcher: {url}")
    print("  ► Press Ctrl+C to stop the server.")
    if not args.no_browser:
        webbrowser.open(url)

    # Keep the foreground attached so Ctrl+C stops the server cleanly.
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  stopping…")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
