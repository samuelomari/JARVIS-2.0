
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# Store the database inside the JARVIS project.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(os.getenv("JARVIS_DATABASE_PATH", PROJECT_ROOT / "data" / "jarvis.db"))


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversation_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                summary TEXT NOT NULL DEFAULT '',
                summarized_through_id INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)

        connection.commit()


def save_message(role, content):
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages (role, content, created_at)
            VALUES (?, ?, ?)
            """,
            (role, content, timestamp)
        )

        connection.commit()


def get_recent_messages(limit=10):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    # Reverse the results so the oldest message comes first.
    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in reversed(rows)
    ]


def get_all_messages(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in reversed(rows)
    ]


def get_conversation_state():
    with get_connection() as connection:
        row = connection.execute(
            "SELECT summary, summarized_through_id FROM conversation_state WHERE id = 1"
        ).fetchone()

    if row is None:
        return {"summary": "", "summarized_through_id": 0}
    return {
        "summary": row["summary"],
        "summarized_through_id": row["summarized_through_id"],
    }


def get_summarizable_messages(summarized_through_id, keep_recent=10):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content
            FROM messages
            WHERE id > ?
            ORDER BY id ASC
            """,
            (summarized_through_id,),
        ).fetchall()

    older_messages = rows[:-keep_recent] if len(rows) > keep_recent else []
    return [dict(row) for row in older_messages]


def save_conversation_summary(summary, summarized_through_id):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO conversation_state (id, summary, summarized_through_id, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                summary = excluded.summary,
                summarized_through_id = excluded.summarized_through_id,
                updated_at = excluded.updated_at
            """,
            (summary, summarized_through_id, timestamp),
        )
        connection.commit()
