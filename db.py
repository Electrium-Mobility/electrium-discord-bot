"""SQLite persistence layer (Task F3).

The three MVP features share this small database:

  * members — who joined and which sub-team they picked (Track A)
  * events  — scheduled meetings/events (Track B)
  * rsvps   — one row per (event, user) response (Track B)

Synchronous sqlite3 is intentional. The queries here are tiny and hit a local
file, so they complete in well under a millisecond and don't meaningfully block
the bot's async event loop. If DB usage ever gets heavy, swap to aiosqlite.

All timestamps are stored as ISO-8601 strings in UTC. Callers format/parse with
datetime; this layer just stores the strings.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import config

DB_PATH = Path(config.DB_PATH)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, always close. Rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                user_id   INTEGER PRIMARY KEY,
                sub_team  TEXT,
                joined_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                starts_at  TEXT    NOT NULL,            -- ISO-8601 UTC
                location   TEXT,
                channel_id INTEGER,                     -- where the event message was posted
                message_id INTEGER,                     -- the event embed's message id
                reminded   INTEGER NOT NULL DEFAULT 0,  -- 0/1: has the reminder fired?
                created_by INTEGER NOT NULL,
                created_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rsvps (
                event_id     INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                status       TEXT    NOT NULL,          -- 'going' | 'maybe' | 'cant'
                responded_at TEXT    NOT NULL,
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            );
            """
        )


# --- members (Track A) ------------------------------------------------------

def upsert_member(user_id: int, joined_at: str) -> None:
    """Record that a member exists. Leaves sub_team untouched if already present."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO members (user_id, joined_at) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO NOTHING",
            (user_id, joined_at),
        )


def set_sub_team(user_id: int, sub_team: str, joined_at: str) -> None:
    """Set/replace a member's chosen sub-team (creates the row if needed)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO members (user_id, sub_team, joined_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET sub_team = excluded.sub_team",
            (user_id, sub_team, joined_at),
        )


# --- events (Track B) -------------------------------------------------------

def add_event(
    title: str,
    starts_at: str,
    location: Optional[str],
    created_by: int,
    created_at: str,
) -> int:
    """Insert an event and return its new id."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, starts_at, location, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, starts_at, location, created_by, created_at),
        )
        return int(cur.lastrowid)


def attach_message(event_id: int, channel_id: int, message_id: int) -> None:
    """Remember where an event's embed was posted, so reminders can reference it."""
    with _connect() as conn:
        conn.execute(
            "UPDATE events SET channel_id = ?, message_id = ? WHERE id = ?",
            (channel_id, message_id, event_id),
        )


def get_event(event_id: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()


def get_unreminded_events_before(threshold: str) -> list[sqlite3.Row]:
    """Events that start at or before `threshold` (ISO UTC) and haven't been reminded.

    The reminder scheduler (Task B3) calls this with `now + reminder_window`.
    """
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM events WHERE reminded = 0 AND starts_at <= ? ORDER BY starts_at",
            (threshold,),
        ).fetchall()


def mark_reminded(event_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE events SET reminded = 1 WHERE id = ?", (event_id,))


# --- rsvps (Track B) --------------------------------------------------------

def set_rsvp(event_id: int, user_id: int, status: str, responded_at: str) -> None:
    """Record or update one member's RSVP. One response per (event, user)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO rsvps (event_id, user_id, status, responded_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(event_id, user_id) DO UPDATE SET "
            "status = excluded.status, responded_at = excluded.responded_at",
            (event_id, user_id, status, responded_at),
        )


def get_rsvp_counts(event_id: int) -> dict[str, int]:
    """Return {'going': n, 'maybe': n, 'cant': n} for an event."""
    counts = {"going": 0, "maybe": 0, "cant": 0}
    with _connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM rsvps WHERE event_id = ? GROUP BY status",
            (event_id,),
        ).fetchall()
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] = row["n"]
    return counts


def get_rsvps_by_status(event_id: int, status: str) -> list[int]:
    """Return the user ids who responded with a given status (for reminder pings)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT user_id FROM rsvps WHERE event_id = ? AND status = ?",
            (event_id, status),
        ).fetchall()
    return [row["user_id"] for row in rows]
