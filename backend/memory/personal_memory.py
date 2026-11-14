import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(os.getenv("JARVIS_DATABASE_PATH", PROJECT_ROOT / "data" / "jarvis.db"))


def _normalize_content(content):
    return " ".join(content.casefold().split())


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_personal_memory():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def add_memory(content, category="general", title=None):
    cleaned_content = (content or "").strip()
    if not cleaned_content:
        raise ValueError("Memory content cannot be empty.")

    normalized_title = (title or "memory").strip() or "memory"
    normalized_category = (category or "general").strip() or "general"

    with get_connection() as connection:
        existing_rows = connection.execute(
            """
            SELECT id, content FROM memories
            WHERE LOWER(category) = LOWER(?)
            ORDER BY id ASC
            """,
            (normalized_category,),
        ).fetchall()
        existing = next(
            (row for row in existing_rows if _normalize_content(row["content"]) == _normalize_content(cleaned_content)),
            None,
        )
        if existing:
            return existing["id"]

        created_at = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            """
            INSERT INTO memories (title, category, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (normalized_title, normalized_category, cleaned_content, created_at),
        )
        connection.commit()

    return cursor.lastrowid


def update_memory(memory_id, content, category="general", title=None):
    cleaned_content = (content or "").strip()
    if not cleaned_content:
        raise ValueError("Memory content cannot be empty.")

    normalized_title = (title or "memory").strip() or "memory"
    normalized_category = (category or "general").strip() or "general"
    with get_connection() as connection:
        existing_rows = connection.execute(
            """
            SELECT id, content FROM memories
            WHERE id != ? AND LOWER(category) = LOWER(?)
            """,
            (memory_id, normalized_category),
        ).fetchall()
        duplicate = any(
            _normalize_content(row["content"]) == _normalize_content(cleaned_content)
            for row in existing_rows
        )
        if duplicate:
            raise ValueError("An equivalent memory already exists in this category.")
        cursor = connection.execute(
            """
            UPDATE memories SET title = ?, category = ?, content = ? WHERE id = ?
            """,
            (normalized_title, normalized_category, cleaned_content, memory_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, category, content, created_at FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
    return dict(row)


def list_memories(limit=20):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, category, content, created_at
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_memory(memory_id):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, category, content, created_at
            FROM memories WHERE id = ?
            """,
            (memory_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_memory(memory_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,),
        )
        connection.commit()
    return cursor.rowcount > 0


def get_relevant_memories(search_text, limit=3):
    query = (search_text or "").strip()
    if not query:
        return []

    token = f"%{query.lower()}%"

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, category, content
            FROM memories
            WHERE LOWER(title) LIKE ?
               OR LOWER(category) LIKE ?
               OR LOWER(content) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (token, token, token, limit),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
        }
        for row in rows
    ]
