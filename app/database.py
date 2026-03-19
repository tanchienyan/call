"""SQLite database layer for missions, steps, and results."""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "data/mystery.db"))


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS missions (
        id TEXT PRIMARY KEY,
        hotel_name TEXT NOT NULL,
        hotel_website TEXT,
        hotel_email TEXT,
        hotel_phone TEXT,
        hotel_whatsapp TEXT,
        persona_name TEXT DEFAULT 'Sarah Mitchell',
        persona_background TEXT,
        status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
        overall_score INTEGER,
        analysis_json TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id TEXT NOT NULL REFERENCES missions(id),
        step_order INTEGER NOT NULL,
        step_type TEXT NOT NULL,
        step_name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        config_json TEXT,
        data_sent TEXT,
        data_received TEXT,
        response_time_seconds REAL,
        score INTEGER,
        sentiment_json TEXT,
        notes TEXT,
        screenshots_json TEXT,
        recording_url TEXT,
        transcript TEXT,
        started_at TEXT,
        completed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS call_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id TEXT REFERENCES missions(id),
        step_id INTEGER REFERENCES steps(id),
        retell_call_id TEXT,
        call_type TEXT,  -- phone_call, web_call
        from_number TEXT,
        to_number TEXT,
        duration_seconds REAL,
        transcript TEXT,
        recording_url TEXT,
        cost_cents REAL,
        analysis_json TEXT,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_steps_mission ON steps(mission_id);
    CREATE INDEX IF NOT EXISTS idx_calls_mission ON call_records(mission_id);
    """)
    conn.commit()
    conn.close()


# ─── Mission CRUD ───

def create_mission(mission_id: str, hotel_name: str, **kwargs) -> dict:
    conn = get_db()
    conn.execute(
        """INSERT INTO missions (id, hotel_name, hotel_website, hotel_email, hotel_phone,
           hotel_whatsapp, persona_name, persona_background, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (mission_id, hotel_name,
         kwargs.get("hotel_website", ""),
         kwargs.get("hotel_email", ""),
         kwargs.get("hotel_phone", ""),
         kwargs.get("hotel_whatsapp", ""),
         kwargs.get("persona_name", "Sarah Mitchell"),
         kwargs.get("persona_background", "Business traveler, tech conference"),
         datetime.utcnow().isoformat())
    )
    conn.commit()
    row = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    conn.close()
    return dict(row)


def get_mission(mission_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_missions(limit=50, offset=0) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM missions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_mission(mission_id: str, **kwargs):
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(mission_id)
    conn.execute(f"UPDATE missions SET {','.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


# ─── Step CRUD ───

def create_step(mission_id: str, step_order: int, step_type: str, step_name: str, config: dict = None) -> int:
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO steps (mission_id, step_order, step_type, step_name, config_json, status)
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (mission_id, step_order, step_type, step_name, json.dumps(config or {}))
    )
    conn.commit()
    step_id = cur.lastrowid
    conn.close()
    return step_id


def update_step(step_id: int, **kwargs):
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k.endswith("_json") and isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(step_id)
    conn.execute(f"UPDATE steps SET {','.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def get_steps(mission_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM steps WHERE mission_id=? ORDER BY step_order", (mission_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Call records ───

def save_call_record(mission_id: str, step_id: int, **kwargs) -> int:
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO call_records (mission_id, step_id, retell_call_id, call_type,
           from_number, to_number, duration_seconds, transcript, recording_url,
           cost_cents, analysis_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mission_id, step_id,
         kwargs.get("retell_call_id", ""),
         kwargs.get("call_type", "phone_call"),
         kwargs.get("from_number", ""),
         kwargs.get("to_number", ""),
         kwargs.get("duration_seconds", 0),
         kwargs.get("transcript", ""),
         kwargs.get("recording_url", ""),
         kwargs.get("cost_cents", 0),
         json.dumps(kwargs.get("analysis", {}), ensure_ascii=False),
         datetime.utcnow().isoformat())
    )
    conn.commit()
    call_id = cur.lastrowid
    conn.close()
    return call_id


def get_call_records(mission_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM call_records WHERE mission_id=? ORDER BY created_at", (mission_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
