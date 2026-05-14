"""Runtime config — JSON sidecar at /app/data/runtime_config.json.

Lets the user set API keys + Composio connection state from the UI without
editing .env or restarting the backend. Every service that needs a key reads
via the helpers below: runtime override → settings (env) → empty.
"""
from __future__ import annotations
import json
import threading
from pathlib import Path
from config import settings

_PATH = Path("/app/data/runtime_config.json")
_LOCK = threading.Lock()
_CACHE: dict | None = None


def _ensure_dir() -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _ensure_dir()
            if _PATH.exists():
                try:
                    _CACHE = json.loads(_PATH.read_text(encoding="utf-8"))
                except Exception:
                    _CACHE = {}
            else:
                _CACHE = {}
        return dict(_CACHE)


def save(patch: dict) -> dict:
    """Merge `patch` into stored config and persist. Pass None to clear a key."""
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            load()
        data = dict(_CACHE or {})
        for k, v in patch.items():
            if v is None:
                data.pop(k, None)
            else:
                data[k] = v
        _ensure_dir()
        _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _CACHE = data
        return dict(data)


def get(key: str, env_fallback: str | None = None) -> str | None:
    v = load().get(key)
    if v in (None, ""):
        return env_fallback
    return v


def set_value(key: str, value: str | None) -> None:
    save({key: value})


# ---- typed helpers used by services ----

def openai_api_key() -> str:
    return get("openai_api_key", settings.openai_api_key) or ""


def tavily_api_key() -> str:
    return get("tavily_api_key", settings.tavily_api_key) or ""


def apify_token() -> str:
    return get("apify_token", settings.apify_token) or ""


def composio_api_key() -> str:
    return get("composio_api_key", settings.composio_api_key) or ""


def composio_entity_id() -> str:
    return get("composio_entity_id", settings.composio_entity_id) or "default"


def composio_auth_config_id() -> str:
    return get("composio_gmail_auth_config", "") or ""


def composio_connection_id() -> str:
    return get("composio_connection_id", "") or ""


def composio_pending_connection_id() -> str:
    return get("composio_pending_connection_id", "") or ""
