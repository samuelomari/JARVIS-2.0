#!/usr/bin/env python3
"""Deterministic checks for JARVIS intelligence, productivity, automation, and online APIs."""

import asyncio
from pathlib import Path
import sys
import tempfile
from unittest.mock import AsyncMock, patch

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.automation.actions import execute_action, preview_action
from backend.automation import actions
from backend.core.intent import classify_intent
from backend.integrations.online import SearchResultParser
from backend.main import app
from backend.memory import database, personal_memory
from backend.memory.productivity import initialize_productivity


async def verify() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        test_database = Path(temp_dir) / "jarvis-test.db"
        database.DATABASE_PATH = test_database
        personal_memory.DATABASE_PATH = test_database
        database.initialize_database()
        personal_memory.initialize_personal_memory()
        initialize_productivity()

        memory_id = personal_memory.add_memory("  I prefer   concise updates ", "preferences", "Writing")
        duplicate_id = personal_memory.add_memory("i prefer concise updates", "PREFERENCES", "Duplicate")
        assert duplicate_id == memory_id
        updated = personal_memory.update_memory(memory_id, "I prefer concise status updates", "preferences", "Style")
        assert updated["title"] == "Style"

        for index in range(32):
            database.save_message("user" if index % 2 == 0 else "assistant", f"context {index}")
        summarizable = database.get_summarizable_messages(0, keep_recent=10)
        assert len(summarizable) == 22
        database.save_conversation_summary("User prefers concise status updates.", summarizable[-1]["id"])
        assert database.get_conversation_state()["summarized_through_id"] == summarizable[-1]["id"]
        assert classify_intent("Create a task for Friday") == "productivity"
        assert classify_intent("Find files named budget") == "desktop_action"

        preview = preview_action("What is the current time?")
        assert execute_action(preview)["result"]
        assert preview_action("Open VS Code")["requires_confirmation"] is True
        try:
            preview_action("run an arbitrary shell command")
        except ValueError:
            pass
        else:
            raise AssertionError("An unapproved desktop action was accepted.")

        with tempfile.TemporaryDirectory() as file_dir:
            search_root = Path(file_dir)
            sample_file = search_root / "sample.txt"
            sample_file.write_text("metadata only", encoding="utf-8")
            with patch.object(actions, "SEARCH_PATHS", (search_root,)):
                info_action = preview_action("file info sample.txt")
                info_result = execute_action(info_action)
                assert info_result["contents_read"] is False
                assert info_result["result"][0]["size_bytes"] == len("metadata only")

        parser = SearchResultParser()
        parser.feed('<a class="result__a" href="https://example.com">Example</a>')
        parser.feed('<a class="result__a" href="javascript:alert(1)">Unsafe</a>')
        assert len(parser.results) == 1 and parser.results[0]["title"] == "Example"

        for index in range(20):
            database.save_message("user" if index % 2 == 0 else "assistant", f"later context {index}")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://jarvis.test") as client:
            memory_response = await client.post("/memory", json={
                "title": "Preferred updates",
                "category": "preferences",
                "content": "Concise status updates",
            })
            assert memory_response.status_code == 200
            memory_id = memory_response.json()["memory"]["id"]
            duplicate_response = await client.post("/memory", json={
                "title": "Alternate title",
                "category": "PREFERENCES",
                "content": " concise   status updates ",
            })
            assert duplicate_response.json()["memory"]["id"] == memory_id
            assert duplicate_response.json()["memory"]["title"] == "Preferred updates"
            edited_response = await client.put(f"/memory/{memory_id}", json={
                "title": "Updated preference",
                "category": "preferences",
                "content": "Short status updates",
            })
            assert edited_response.json()["memory"]["title"] == "Updated preference"

            with patch("backend.main.ask_jarvis", new=AsyncMock(return_value="Local test reply")), patch(
                "backend.main.summarize_conversation",
                new=AsyncMock(return_value="User prefers concise status updates."),
            ) as summarize_mock:
                response = await client.post("/chat", json={"message": "Create a task for tomorrow"})
                assert response.status_code == 200
                assert response.json()["intent"] == "productivity"
                summarize_mock.assert_awaited_once()
                assert database.get_conversation_state()["summary"] == "User prefers concise status updates."

            note_response = await client.post("/notes", json={"title": "Test", "content": "A note"})
            assert note_response.status_code == 200
            search_notes_response = await client.get("/notes/search", params={"query": "note"})
            assert search_notes_response.json()["notes"][0]["title"] == "Test"
            task_response = await client.post("/tasks", json={"title": "Test task"})
            task_id = task_response.json()["task"]["id"]
            completed = await client.patch(f"/tasks/{task_id}", json={"status": "completed"})
            assert completed.json()["task"]["status"] == "completed"
            due_at = "2000-01-01T00:00:00+00:00"
            reminder_response = await client.post("/reminders", json={"title": "Test reminder", "remind_at": due_at})
            reminder_id = reminder_response.json()["reminder"]["id"]
            assert (await client.get("/reminders/due")).json()["reminders"][0]["id"] == reminder_id
            acknowledged = await client.post(f"/reminders/{reminder_id}/acknowledge")
            assert acknowledged.json()["reminder"]["status"] == "notified"

            with patch("backend.main.search_web", new=AsyncMock(return_value=[
                {"title": "Example result", "url": "https://example.com"}
            ])):
                response = await client.get("/search", params={"query": "local test"})
                assert response.status_code == 200
                assert response.json()["results"][0]["title"] == "Example result"

            with patch("backend.main.lookup_weather", new=AsyncMock(return_value={
                "location": {"name": "Test City"}, "current": {"temperature_2m": 18}
            })):
                response = await client.get("/integrations/weather", params={"location": "Test City"})
                assert response.status_code == 200

            with patch("backend.main.get_public_github_repository", new=AsyncMock(return_value={
                "name": "owner/repo", "stars": 12
            })):
                response = await client.get("/integrations/github/owner/repo")
                assert response.status_code == 200 and response.json()["stars"] == 12

            system_response = await client.get("/system/status")
            assert system_response.status_code == 200
            assert "cpu_count" in system_response.json()

            action_response = await client.post("/automation/preview", json={"command": "Open VS Code"})
            assert action_response.status_code == 200
            action_payload = {
                "preview_id": action_response.json()["preview_id"],
                "confirmed": False,
            }
            assert (await client.post("/automation/execute", json=action_payload)).status_code == 400
            action_payload["confirmed"] = True
            with patch("backend.main.execute_action", return_value={"result": "Launched vscode."}):
                execute_response = await client.post("/automation/execute", json=action_payload)
            assert execute_response.status_code == 200
            assert (await client.post("/automation/execute", json=action_payload)).status_code == 410


def main() -> None:
    asyncio.run(verify())
    print("Extended feature verification passed: intelligence, memory, productivity, actions, and opt-in APIs.")


if __name__ == "__main__":
    main()