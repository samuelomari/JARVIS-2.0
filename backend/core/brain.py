
import os

import httpx

OLLAMA_BASE_URL = os.getenv("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"
MODEL = os.getenv("JARVIS_MODEL", "qwen2.5:1.5b-instruct")


async def get_engine_status():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = [
            item["name"]
            for item in data.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
        model_available = MODEL in models
        return {
            "status": "ready" if model_available else "model_missing",
            "connected": True,
            "model": MODEL,
            "model_available": model_available,
            "models": models,
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {
            "status": "unavailable",
            "connected": False,
            "model": MODEL,
            "model_available": False,
            "models": [],
        }


async def select_model(model_name: str):
    global MODEL

    normalized_name = model_name.strip()
    if not normalized_name:
        raise ValueError("Model name cannot be empty.")

    status = await get_engine_status()
    if not status["connected"]:
        raise RuntimeError("Ollama is not available.")
    if normalized_name not in status["models"]:
        raise ValueError("The requested model is not installed in Ollama.")

    MODEL = normalized_name
    status["model"] = MODEL
    status["model_available"] = True
    status["status"] = "ready"
    return status


async def summarize_conversation(previous_summary, messages):
    transcript = "\n".join(
        f"{item['role']}: {item['content']}" for item in messages
    )
    prompt = (
        "Update this concise conversation memory using only information stated in the transcript. "
        "Preserve useful user preferences, ongoing projects, decisions, and unresolved tasks. "
        "Do not invent facts. Return only the updated summary.\n\n"
        f"Existing summary:\n{previous_summary or '(none)'}\n\n"
        f"New transcript:\n{transcript}"
    )
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "Summarize conversation context faithfully."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
        return result.get("message", {}).get("content", "").strip() or None
    except (httpx.HTTPError, AttributeError, TypeError, ValueError):
        return None

SYSTEM_PROMPT = """
You are JARVIS, a personal AI desktop assistant.

Your responsibilities:
- Answer questions clearly.
- Help with programming and technology.
- Assist with computer productivity.
- Communicate professionally and naturally.
- Be concise but helpful.
- Use personal memory context when it is relevant to the user's request.

You are running locally on the user's computer.
Never claim to have performed an action unless it
has actually been completed.
"""


async def ask_jarvis(
    message: str,
    history=None,
    memory_context=None,
    conversation_summary=None,
    intent="general",
):
    if history is None:
        history = []
    if memory_context is None:
        memory_context = []

    memory_text = ""
    if memory_context:
        memory_lines = [
            f"- {entry.get('title', 'Memory')}: {entry.get('content', '')}"
            for entry in memory_context
        ]
        memory_text = "Relevant personal memories:\n" + "\n".join(memory_lines) + "\n\n"

    user_content = f"{memory_text}User question: {message}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_summary:
        messages.append({
            "role": "system",
            "content": f"Summary of earlier conversation for continuity:\n{conversation_summary}",
        })
    messages.extend([
        *history[-10:],
        {"role": "user", "content": f"Detected request category: {intent}.\n{user_content}"},
    ])

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

        if not result or "message" not in result or "content" not in result["message"]:
            return "I received an empty response from my model. Please check that the local AI engine is available and try again."

        return result["message"]["content"].strip() or "I don't have a response available for that yet."
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return (
            "I could not reach my local AI engine. Please confirm that Ollama is running "
            "and that the qwen2.5:1.5b-instruct model is installed on this computer."
        )
