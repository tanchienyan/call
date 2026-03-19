"""SQLite storage for calls and transcripts."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/calls.db")


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
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
    conn.commit()
    conn.close()


def create_call(call_id: str, to_number: str, from_number: str,
                agent_name: str, agent_scenario: str, voice_id: str) -> dict:
    conn = get_db()
    conn.execute(
        """INSERT INTO calls (id, to_number, from_number, agent_name, agent_scenario, 
           voice_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'initiating', ?)""",
        (call_id, to_number, from_number, agent_name, agent_scenario, voice_id,
         datetime.utcnow().isoformat())
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
    return d


def list_calls(limit=50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)
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
