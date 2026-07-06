from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "simworld.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in _existing_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                job TEXT NOT NULL,
                home TEXT NOT NULL,
                personality TEXT NOT NULL,
                ambition INTEGER NOT NULL,
                sociability INTEGER NOT NULL,
                stability INTEGER NOT NULL,
                wealth INTEGER NOT NULL,
                happiness INTEGER NOT NULL,
                energy INTEGER NOT NULL,
                health INTEGER NOT NULL,
                relationship_status TEXT NOT NULL,
                partner_id INTEGER,
                story_arc TEXT NOT NULL,
                life_goal TEXT NOT NULL DEFAULT '',
                dramatic_need TEXT NOT NULL DEFAULT '',
                secret TEXT NOT NULL DEFAULT '',
                secret_status TEXT NOT NULL DEFAULT 'hidden',
                memory_summary TEXT NOT NULL,
                created_day INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(partner_id) REFERENCES people(id)
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_a INTEGER NOT NULL,
                person_b INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                trust INTEGER NOT NULL DEFAULT 50,
                attraction INTEGER NOT NULL DEFAULT 10,
                jealousy INTEGER NOT NULL DEFAULT 0,
                dependency INTEGER NOT NULL DEFAULT 10,
                resentment INTEGER NOT NULL DEFAULT 0,
                history TEXT NOT NULL DEFAULT '',
                UNIQUE(person_a, person_b),
                FOREIGN KEY(person_a) REFERENCES people(id),
                FOREIGN KEY(person_b) REFERENCES people(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                importance INTEGER NOT NULL,
                people_ids TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                notable TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scene_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL,
                title TEXT NOT NULL,
                viewpoint_person_id INTEGER,
                scene_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                emotional_turn TEXT NOT NULL,
                involved_ids TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(viewpoint_person_id) REFERENCES people(id)
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                day INTEGER NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                memory_type TEXT NOT NULL DEFAULT 'event',
                text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES people(id)
            );

            CREATE TABLE IF NOT EXISTS director_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL UNIQUE,
                focus_people_ids TEXT NOT NULL,
                diagnosis TEXT NOT NULL,
                tomorrow_hooks TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chapter_outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                theme TEXT NOT NULL,
                protagonist_ids TEXT NOT NULL,
                outline TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL,
                scene_id INTEGER,
                event_id INTEGER,
                mode TEXT NOT NULL DEFAULT 'dialogue',
                title TEXT NOT NULL,
                viewpoint_person_id INTEGER,
                partner_person_id INTEGER,
                text TEXT NOT NULL,
                ai_generated INTEGER NOT NULL DEFAULT 0,
                importance INTEGER NOT NULL DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(scene_id, mode),
                FOREIGN KEY(scene_id) REFERENCES scene_cards(id),
                FOREIGN KEY(event_id) REFERENCES events(id),
                FOREIGN KEY(viewpoint_person_id) REFERENCES people(id),
                FOREIGN KEY(partner_person_id) REFERENCES people(id)
            );



            CREATE TABLE IF NOT EXISTS serial_stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                subtitle TEXT NOT NULL DEFAULT '',
                protagonist_id INTEGER,
                supporting_ids TEXT NOT NULL DEFAULT '[]',
                theme TEXT NOT NULL DEFAULT '',
                story_text TEXT NOT NULL,
                tomorrow_hook TEXT NOT NULL DEFAULT '',
                ai_generated INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(protagonist_id) REFERENCES people(id)
            );



            CREATE TABLE IF NOT EXISTS gossip_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL UNIQUE,
                headline TEXT NOT NULL,
                hot_topics TEXT NOT NULL,
                danger_people TEXT NOT NULL,
                secret_watch TEXT NOT NULL,
                runaway_watch TEXT NOT NULL,
                relationship_bombs TEXT NOT NULL,
                town_mood TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                day INTEGER PRIMARY KEY,
                avg_happiness REAL NOT NULL,
                avg_energy REAL NOT NULL,
                avg_health REAL NOT NULL,
                avg_wealth REAL NOT NULL,
                low_happiness_count INTEGER NOT NULL,
                low_health_count INTEGER NOT NULL,
                partnered_count INTEGER NOT NULL,
                event_count INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_events_day ON events(day DESC, importance DESC);
            CREATE INDEX IF NOT EXISTS idx_scene_cards_day ON scene_cards(day DESC, importance DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_person_day ON memories(person_id, day DESC, importance DESC);
            CREATE INDEX IF NOT EXISTS idx_director_notes_day ON director_notes(day DESC);
            CREATE INDEX IF NOT EXISTS idx_chapter_outlines_day ON chapter_outlines(day DESC);
            CREATE INDEX IF NOT EXISTS idx_conversations_day ON conversations(day DESC, importance DESC);
            CREATE INDEX IF NOT EXISTS idx_conversations_scene ON conversations(scene_id, mode);
            CREATE INDEX IF NOT EXISTS idx_serial_stories_day ON serial_stories(day DESC);
            CREATE INDEX IF NOT EXISTS idx_gossip_reports_day ON gossip_reports(day DESC);

            CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
            """
        )

        # V3 migrations for users who copy an older simworld.db into this folder.
        _add_column_if_missing(conn, "people", "life_goal", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "people", "dramatic_need", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "people", "secret", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "people", "secret_status", "TEXT NOT NULL DEFAULT 'hidden'")
        _add_column_if_missing(conn, "relationships", "trust", "INTEGER NOT NULL DEFAULT 50")
        _add_column_if_missing(conn, "relationships", "attraction", "INTEGER NOT NULL DEFAULT 10")
        _add_column_if_missing(conn, "relationships", "jealousy", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "relationships", "dependency", "INTEGER NOT NULL DEFAULT 10")
        _add_column_if_missing(conn, "relationships", "resentment", "INTEGER NOT NULL DEFAULT 0")

        defaults = {
            "day": "0",
            "world_name": "M6 Town",
            "auto_enabled": "0",
            "auto_interval_minutes": "1440",
            "auto_use_ai": "0",
            "last_auto_timestamp": "0",
            "director_style": "literary",
            "v4_scene_ai": "0",
            "auto_story_enabled": "1",
            "auto_story_export": "1",
            "auto_story_use_ai": "0",
            "auto_story_catchup": "1",
            "story_last_opened_day": "0",
        }
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO world_state(key, value) VALUES(?, ?)", (key, value))
        conn.commit()


def get_state(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM world_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_state(key: str, value: Any) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO world_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        conn.commit()


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        return list(conn.execute(sql, tuple(params)).fetchall())


def fetch_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(sql, tuple(params)).fetchone()


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def encode_ids(ids: list[int]) -> str:
    return json.dumps(ids, ensure_ascii=False)


def decode_ids(value: str) -> list[int]:
    try:
        return [int(x) for x in json.loads(value)]
    except Exception:
        return []
