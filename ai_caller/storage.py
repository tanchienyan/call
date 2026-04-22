"""SQLite storage for calls, transcripts, and corpus labels.

Schema design note: as of docs/developer_plan.md §4.1 the `calls` table carries
the first-class labels that make the corpus queryable (outcome, language,
consent_recording, compliance_flags_json, qa_score, brand_id, channel,
is_synthetic). These are persisted by the write paths in `qa_engine.py`,
`web_session.py`, and `pipeline.py` so every live call feeds the corpus
moat. See docs/developer_plan.md §9 for how this supports the Series A narrative.

The table remains named `calls` for now. §4.8 of the plan will rename it to
`conversations` once the WhatsApp channel lands; the `channel` column here
is the forward-compatible hook.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/calls.db")


# Columns added after the original CREATE TABLE. Each one is ALTER-added
# on startup if missing, so existing DBs upgrade in place.
_LABEL_COLUMNS: list[tuple[str, str]] = [
    ("outcome", "TEXT"),
    ("outcome_source", "TEXT"),  # 'qa_engine' | 'human' | 'synth'
    ("language", "TEXT"),
    ("consent_recording", "INTEGER DEFAULT 0"),
    ("compliance_flags_json", "TEXT"),
    ("qa_score", "REAL"),
    ("brand_id", "TEXT"),
    ("channel", "TEXT DEFAULT 'voice'"),
    ("is_synthetic", "INTEGER DEFAULT 0"),
]


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the table and ensure all label columns exist.

    Uses ALTER TABLE ADD COLUMN IF NOT EXISTS semantics by checking
    PRAGMA table_info, because SQLite versions shipped with macOS/
    Python stdlib don't all support `ADD COLUMN IF NOT EXISTS`.
    """
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS calls (
        id TEXT PRIMARY KEY,
        to_number TEXT NOT NULL,
        from_number TEXT,
        agent_name TEXT,
        agent_scenario TEXT,
        voice_id TEXT,
        status TEXT DEFAULT 'initiating',
        twilio_call_sid TEXT,
        duration_seconds REAL DEFAULT 0,
        transcript TEXT DEFAULT '[]',
        summary TEXT,
        cost_estimate_cents REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        started_at TEXT,
        ended_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_calls_created ON calls(created_at DESC);
    """)

    existing = {row["name"] for row in conn.execute("PRAGMA table_info(calls)").fetchall()}
    for name, decl in _LABEL_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE calls ADD COLUMN {name} {decl}")

    # Helpful indices for corpus queries and fleet aggregation
    conn.executescript("""
    CREATE INDEX IF NOT EXISTS idx_calls_outcome ON calls(outcome);
    CREATE INDEX IF NOT EXISTS idx_calls_brand ON calls(brand_id);
    CREATE INDEX IF NOT EXISTS idx_calls_synth ON calls(is_synthetic);
    CREATE INDEX IF NOT EXISTS idx_calls_channel ON calls(channel);
    """)

    conn.commit()
    conn.close()


def create_call(call_id: str, to_number: str, from_number: str,
                agent_name: str, agent_scenario: str, voice_id: str,
                brand_id: str | None = None,
                channel: str = "voice",
                language: str | None = None,
                is_synthetic: bool = False) -> dict:
    conn = get_db()
    conn.execute(
        """INSERT INTO calls (id, to_number, from_number, agent_name, agent_scenario,
           voice_id, status, created_at, brand_id, channel, language, is_synthetic)
           VALUES (?, ?, ?, ?, ?, ?, 'initiating', ?, ?, ?, ?, ?)""",
        (call_id, to_number, from_number, agent_name, agent_scenario, voice_id,
         datetime.utcnow().isoformat(), brand_id, channel, language,
         1 if is_synthetic else 0)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    conn.close()
    return dict(row)


def update_call(call_id: str, **kwargs):
    conn = get_db()
    sets, vals = [], []
    for k, v in kwargs.items():
        sets.append(f"{k}=?")
        vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
    vals.append(call_id)
    conn.execute(f"UPDATE calls SET {','.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def set_labels(call_id: str, *,
               outcome: str | None = None,
               outcome_source: str | None = None,
               language: str | None = None,
               consent_recording: bool | None = None,
               compliance_flags: list | None = None,
               qa_score: float | None = None,
               brand_id: str | None = None) -> None:
    """Write the first-class label columns on a call.

    Only provided fields are written; others are left untouched. This is
    the canonical write path for corpus labels — avoid passing these via
    generic update_call() so the schema stays discoverable.
    """
    updates: dict = {}
    if outcome is not None:
        updates["outcome"] = outcome
    if outcome_source is not None:
        updates["outcome_source"] = outcome_source
    if language is not None:
        updates["language"] = language
    if consent_recording is not None:
        updates["consent_recording"] = 1 if consent_recording else 0
    if compliance_flags is not None:
        updates["compliance_flags_json"] = json.dumps(compliance_flags, ensure_ascii=False)
    if qa_score is not None:
        updates["qa_score"] = qa_score
    if brand_id is not None:
        updates["brand_id"] = brand_id

    if updates:
        update_call(call_id, **updates)


def get_call(call_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["transcript"] = json.loads(d["transcript"])
    except (json.JSONDecodeError, TypeError):
        d["transcript"] = []
    if d.get("compliance_flags_json"):
        try:
            d["compliance_flags"] = json.loads(d["compliance_flags_json"])
        except (json.JSONDecodeError, TypeError):
            d["compliance_flags"] = []
    return d


def list_calls(limit=50, *, include_synthetic: bool = True,
               brand_id: str | None = None,
               channel: str | None = None) -> list[dict]:
    conn = get_db()
    where = ["1=1"]
    params: list = []
    if not include_synthetic:
        where.append("is_synthetic=0")
    if brand_id:
        where.append("brand_id=?")
        params.append(brand_id)
    if channel:
        where.append("channel=?")
        params.append(channel)
    params.append(limit)

    rows = conn.execute(
        f"SELECT * FROM calls WHERE {' AND '.join(where)} "
        "ORDER BY created_at DESC LIMIT ?",
        params,
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        try:
            d["transcript"] = json.loads(d["transcript"])
        except (json.JSONDecodeError, TypeError):
            d["transcript"] = []
        results.append(d)
    return results


def list_calls_with_labels(limit: int = 200,
                           *,
                           outcome: str | None = None,
                           brand_id: str | None = None,
                           language: str | None = None,
                           include_synthetic: bool = False,
                           since: str | None = None) -> list[dict]:
    """Corpus-export oriented query: returns label columns + transcript only.

    Used by the /api/corpus/* endpoints (planned §4.11). Keeps payloads
    small and excludes synthetic calls by default — the corpus moat per
    docs/developer_plan.md §9 is real calls only.
    """
    conn = get_db()
    where = ["1=1"]
    params: list = []
    if not include_synthetic:
        where.append("is_synthetic=0")
    if outcome:
        where.append("outcome=?")
        params.append(outcome)
    if brand_id:
        where.append("brand_id=?")
        params.append(brand_id)
    if language:
        where.append("language=?")
        params.append(language)
    if since:
        where.append("created_at>=?")
        params.append(since)
    params.append(limit)

    rows = conn.execute(
        f"""SELECT id, agent_scenario, brand_id, channel, language, outcome,
                   outcome_source, consent_recording, qa_score,
                   compliance_flags_json, duration_seconds, transcript,
                   created_at
            FROM calls WHERE {' AND '.join(where)}
            ORDER BY created_at DESC LIMIT ?""",
        params,
    ).fetchall()
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        try:
            d["transcript"] = json.loads(d["transcript"])
        except (json.JSONDecodeError, TypeError):
            d["transcript"] = []
        if d.get("compliance_flags_json"):
            try:
                d["compliance_flags"] = json.loads(d["compliance_flags_json"])
            except (json.JSONDecodeError, TypeError):
                d["compliance_flags"] = []
            d.pop("compliance_flags_json", None)
        out.append(d)
    return out


def append_transcript(call_id: str, role: str, text: str):
    """Append a transcript entry."""
    conn = get_db()
    row = conn.execute("SELECT transcript FROM calls WHERE id=?", (call_id,)).fetchone()
    if row:
        try:
            entries = json.loads(row["transcript"])
        except (json.JSONDecodeError, TypeError):
            entries = []
        entries.append({
            "role": role,
            "text": text,
            "ts": datetime.utcnow().isoformat()
        })
        conn.execute("UPDATE calls SET transcript=? WHERE id=?",
                      (json.dumps(entries, ensure_ascii=False), call_id))
        conn.commit()
    conn.close()


init_db()
