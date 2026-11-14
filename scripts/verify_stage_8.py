#!/usr/bin/env python3
"""Stage 8 verification for local Ollama engine management."""

import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core import brain
from backend.main import app


def main() -> None:
    original_model = brain.MODEL
    installed_models = {
        "status": "ready",
        "connected": True,
        "model": original_model,
        "model_available": True,
        "models": [original_model, "llama3.2:latest"],
    }

    async def verify_selection() -> None:
        with patch.object(
            brain,
            "get_engine_status",
            new=AsyncMock(return_value=installed_models.copy()),
        ):
            result = await brain.select_model("llama3.2:latest")
            if result["model"] != "llama3.2:latest" or brain.MODEL != "llama3.2:latest":
                raise RuntimeError("Installed model selection did not update the active model.")

            try:
                await brain.select_model("not-installed:latest")
            except ValueError:
                pass
            else:
                raise RuntimeError("An uninstalled model was incorrectly accepted.")

            unavailable = AsyncMock(return_value={"connected": False, "models": []})
            with patch.object(brain, "get_engine_status", new=unavailable):
                try:
                    await brain.select_model("llama3.2:latest")
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError("Model selection succeeded while Ollama was unavailable.")

    try:
        asyncio.run(verify_selection())
    finally:
        brain.MODEL = original_model

    client = TestClient(app)
    with patch(
        "backend.main.get_engine_status",
        new=AsyncMock(return_value=installed_models),
    ):
        response = client.get("/engine")
        if response.status_code != 200 or response.json()["models"] != installed_models["models"]:
            raise RuntimeError("The engine status endpoint returned an unexpected response.")

    with patch(
        "backend.main.select_model",
        new=AsyncMock(side_effect=RuntimeError("Ollama is not available.")),
    ):
        response = client.put("/engine/model", json={"model": "llama3.2:latest"})
        if response.status_code != 503:
            raise RuntimeError("The model endpoint did not report unavailable Ollama as 503.")

    print("Stage 8 verification passed: engine status and safe model selection work.")


if __name__ == "__main__":
    main()