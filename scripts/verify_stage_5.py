#!/usr/bin/env python3
"""Stage 5 verification for the JARVIS SQLite memory layer.

This script confirms that the project can save messages and reload them from the
SQLite database without losing the conversation history.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.memory.database import (
    get_recent_messages,
    initialize_database,
    save_message,
)


def main() -> None:
    initialize_database()

    marker = "stage5_sqlite_verification"
    save_message("user", marker)
    save_message("assistant", "verified")

    recent = get_recent_messages(limit=10)
    contents = [entry["content"] for entry in recent]

    if marker not in contents:
        raise RuntimeError("SQLite verification failed: user message was not recovered.")

    if "verified" not in contents:
        raise RuntimeError("SQLite verification failed: assistant response was not recovered.")

    print("Stage 5 verification passed: SQLite persists user and assistant messages.")
    print("Recent messages:")
    for entry in recent:
        print(f"- {entry['role']}: {entry['content']}")


if __name__ == "__main__":
    main()
