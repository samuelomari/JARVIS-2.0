from datetime import datetime, timezone

from backend.memory.database import get_connection


def initialize_productivity():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'completed')),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'notified', 'dismissed')),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def create_note(title, content):
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",
            (title.strip(), content.strip(), created_at),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_notes(limit=50):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def search_notes(query, limit=50):
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []
    token = f"%{normalized_query.lower()}%"
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM notes
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (token, token, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def create_task(title, description="", due_at=None):
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, description, due_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (title.strip(), description.strip(), due_at, created_at),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_tasks(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM tasks
            ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def set_task_status(task_id, status):
    if status not in {"pending", "completed"}:
        raise ValueError("Task status must be pending or completed.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row)


def create_reminder(title, remind_at):
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO reminders (title, remind_at, created_at) VALUES (?, ?, ?)",
            (title.strip(), remind_at, timestamp),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def list_reminders(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM reminders ORDER BY remind_at ASC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_due_reminders():
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM reminders
            WHERE status = 'pending' AND remind_at <= ?
            ORDER BY remind_at ASC
            """,
            (now,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_reminder_status(reminder_id, status):
    if status not in {"notified", "dismissed"}:
        raise ValueError("Reminder status is invalid.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE reminders SET status = ? WHERE id = ? AND status = 'pending'",
            (status, reminder_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
    return dict(row)