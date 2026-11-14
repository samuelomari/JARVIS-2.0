#!/usr/bin/env python3
"""Stage 6 verification for JARVIS personal memory features."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.memory.personal_memory import (
    add_memory,
    delete_memory,
    initialize_personal_memory,
    list_memories,
)


def main() -> None:
    initialize_personal_memory()

    memory_text = "Stage 6 memory verification"
    memory_id = add_memory(memory_text, category="project", title="verification")
    memories = list_memories(limit=20)

    if all(item["content"] != memory_text for item in memories):
        raise RuntimeError("Personal memory verification failed: memory was not persisted.")

    delete_memory(memory_id)
    memories_after_delete = list_memories(limit=20)

    if any(item["content"] == memory_text for item in memories_after_delete):
        raise RuntimeError("Personal memory verification failed: memory was not deleted.")

    print("Stage 6 verification passed: personal memory can be saved and removed.")


if __name__ == "__main__":
    main()
