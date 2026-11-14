
from datetime import datetime, timezone
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi import Query

from backend.automation.actions import execute_action, preview_action
from backend.core.brain import (
    ask_jarvis,
    get_engine_status,
    select_model,
    summarize_conversation,
)
from backend.core.intent import classify_intent
from backend.core.system_status import get_system_status
from backend.memory.database import (
    get_conversation_state,
    initialize_database,
    save_message,
    get_recent_messages,
    get_all_messages,
    get_summarizable_messages,
    save_conversation_summary,
)
from backend.memory.personal_memory import (
    add_memory,
    delete_memory,
    get_relevant_memories,
    get_memory,
    initialize_personal_memory,
    list_memories,
    update_memory,
)
from backend.memory.productivity import (
    create_note,
    create_reminder,
    create_task,
    get_due_reminders,
    initialize_productivity,
    list_notes,
    list_reminders,
    list_tasks,
    search_notes,
    set_task_status,
    update_reminder_status,
)
from backend.integrations.online import (
    get_public_github_repository,
    lookup_weather,
    search_web,
)


app = FastAPI(
    title="JARVIS AI",
    description="Personal Hybrid AI Desktop Assistant",
    version="1.0.0"
)


initialize_database()
initialize_personal_memory()
initialize_productivity()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    category: str = Field(default="general", max_length=80)
    title: str | None = Field(default=None, max_length=160)


class EngineModelRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)


class NoteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=5000)


class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    due_at: str | None = None


class TaskStatusRequest(BaseModel):
    status: str = Field(pattern="^(pending|completed)$")


class ReminderRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    remind_at: str = Field(min_length=1, max_length=50)


class AutomationPreviewRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class AutomationExecuteRequest(BaseModel):
    preview_id: str = Field(min_length=1, max_length=100)
    confirmed: bool = False


PENDING_ACTIONS = {}


@app.get("/")
async def home():
    return {
        "assistant": "JARVIS",
        "status": "online",
        "message": "JARVIS AI is ready."
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "assistant": "JARVIS",
        "engine": await get_engine_status(),
    }


@app.get("/system/status")
async def system_status():
    return get_system_status()


@app.get("/engine")
async def engine_status():
    return await get_engine_status()


@app.put("/engine/model")
async def update_engine_model(request: EngineModelRequest):
    try:
        return await select_model(request.model)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/history")
async def history():
    return {
        "assistant": "JARVIS",
        "messages": get_all_messages()
    }


@app.get("/memory")
async def memory_list():
    return {
        "assistant": "JARVIS",
        "memories": list_memories(limit=50)
    }


@app.post("/memory")
async def create_memory(request: MemoryRequest):
    try:
        memory_id = add_memory(
            content=request.content,
            category=request.category,
            title=request.title,
        )
        return {
            "assistant": "JARVIS",
            "memory": get_memory(memory_id),
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.put("/memory/{memory_id}")
async def edit_memory(memory_id: int, request: MemoryRequest):
    try:
        memory = update_memory(
            memory_id,
            content=request.content,
            category=request.category,
            title=request.title,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"assistant": "JARVIS", "memory": memory}


@app.delete("/memory/{memory_id}")
async def remove_memory(memory_id: int):
    if not delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"assistant": "JARVIS", "deleted": True, "id": memory_id}


@app.get("/notes")
async def notes_list():
    return {"notes": list_notes()}


@app.get("/notes/search")
async def notes_search(query: str = Query(min_length=1, max_length=200)):
    return {"notes": search_notes(query)}


@app.post("/notes")
async def note_create(request: NoteRequest):
    return {"note": create_note(request.title, request.content)}


@app.get("/tasks")
async def tasks_list():
    return {"tasks": list_tasks()}


@app.post("/tasks")
async def task_create(request: TaskRequest):
    return {"task": create_task(request.title, request.description, request.due_at)}


@app.patch("/tasks/{task_id}")
async def task_update(task_id: int, request: TaskStatusRequest):
    task = set_task_status(task_id, request.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"task": task}


@app.get("/reminders")
async def reminders_list():
    return {"reminders": list_reminders()}


@app.get("/reminders/due")
async def reminders_due():
    return {"reminders": get_due_reminders()}


@app.post("/reminders")
async def reminder_create(request: ReminderRequest):
    try:
        remind_at = datetime.fromisoformat(request.remind_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="remind_at must be an ISO 8601 timestamp.")
    if remind_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="remind_at must include a timezone.")
    return {"reminder": create_reminder(request.title, remind_at.astimezone(timezone.utc).isoformat())}


@app.post("/reminders/{reminder_id}/dismiss")
async def reminder_dismiss(reminder_id: int):
    reminder = update_reminder_status(reminder_id, "dismissed")
    if reminder is None:
        raise HTTPException(status_code=404, detail="Pending reminder not found.")
    return {"reminder": reminder}


@app.post("/reminders/{reminder_id}/acknowledge")
async def reminder_acknowledge(reminder_id: int):
    reminder = update_reminder_status(reminder_id, "notified")
    if reminder is None:
        raise HTTPException(status_code=404, detail="Pending reminder not found.")
    return {"reminder": reminder}


@app.post("/automation/preview")
async def automation_preview(request: AutomationPreviewRequest):
    try:
        action = preview_action(request.command)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    expired_ids = [
        preview_id
        for preview_id, pending in PENDING_ACTIONS.items()
        if pending["expires_at"] < time.time()
    ]
    for expired_id in expired_ids:
        PENDING_ACTIONS.pop(expired_id, None)
    preview_id = str(uuid.uuid4())
    PENDING_ACTIONS[preview_id] = {"action": action, "expires_at": time.time() + 90}
    return {
        "preview_id": preview_id,
        "display": action["display"],
        "requires_confirmation": action["requires_confirmation"],
    }


@app.post("/automation/execute")
async def automation_execute(request: AutomationExecuteRequest):
    pending = PENDING_ACTIONS.get(request.preview_id)
    if pending is None:
        raise HTTPException(status_code=410, detail="Action preview expired or was already used.")
    if pending["expires_at"] < time.time():
        PENDING_ACTIONS.pop(request.preview_id, None)
        raise HTTPException(status_code=410, detail="Action preview expired or was already used.")
    action = pending["action"]
    if action["requires_confirmation"] and not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    PENDING_ACTIONS.pop(request.preview_id, None)
    try:
        return execute_action(action)
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/search")
async def web_search(query: str = Query(min_length=2, max_length=200)):
    try:
        return {"query": query, "results": await search_web(query)}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Web search failed: {error}")


@app.get("/integrations/weather")
async def weather(location: str = Query(min_length=2, max_length=100)):
    try:
        return await lookup_weather(location)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Weather lookup failed: {error}")


@app.get("/integrations/github/{owner}/{repository}")
async def github_repository(owner: str, repository: str):
    try:
        return await get_public_github_repository(owner, repository)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"GitHub lookup failed: {error}")


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        conversation_history = get_recent_messages(limit=10)
        conversation_state = get_conversation_state()
        summary_candidates = get_summarizable_messages(
            conversation_state["summarized_through_id"],
            keep_recent=10,
        )
        if len(summary_candidates) >= 20:
            updated_summary = await summarize_conversation(
                conversation_state["summary"],
                summary_candidates,
            )
            if updated_summary:
                through_id = summary_candidates[-1]["id"]
                save_conversation_summary(updated_summary, through_id)
                conversation_state = {
                    "summary": updated_summary,
                    "summarized_through_id": through_id,
                }

        relevant_memories = get_relevant_memories(request.message, limit=3)
        intent = classify_intent(request.message)

        save_message("user", request.message)

        reply = await ask_jarvis(
            request.message,
            conversation_history,
            relevant_memories,
            conversation_state["summary"],
            intent,
        )

        save_message("assistant", reply)

        return {
            "assistant": "JARVIS",
            "reply": reply,
            "relevant_memories": relevant_memories,
            "intent": intent,
        }

    except Exception as error:
        print(f"JARVIS error: {error}")

        raise HTTPException(
            status_code=503,
            detail="JARVIS could not process your request."
        )
