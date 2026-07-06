from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def ollama_generate(prompt: str, model: str | None = None, timeout: int = 60) -> str | None:
    """Optional local AI. If Ollama is not running, return None and the app falls back to rules."""
    if os.environ.get("SIMWORLD_USE_OLLAMA", "0") not in {"1", "true", "TRUE", "yes", "YES"}:
        return None

    model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data.get("response", "").strip()
            return text or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
