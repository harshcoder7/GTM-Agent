"""Generic API-key store — OpenAI / Tavily / Apify.

Settings UI uses these endpoints to set/clear/verify keys without editing .env.

  GET  /api/keys              — status (masked previews, configured flags)
  PUT  /api/keys              — set or clear keys
  POST /api/keys/test/<name>  — live verify a key (where applicable)
"""
from __future__ import annotations
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import runtime_config

router = APIRouter(prefix="/api/keys", tags=["keys"])


class KeysPatch(BaseModel):
    openai_api_key: str | None = None
    tavily_api_key: str | None = None
    apify_token: str | None = None


def _mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return "•" * len(s)
    return f"{s[:4]}…{s[-4:]}"


@router.get("")
def get_keys():
    return {
        "openai": {
            "configured": bool(runtime_config.openai_api_key()),
            "preview": _mask(runtime_config.openai_api_key()),
        },
        "tavily": {
            "configured": bool(runtime_config.tavily_api_key()),
            "preview": _mask(runtime_config.tavily_api_key()),
        },
        "apify": {
            "configured": bool(runtime_config.apify_token()),
            "preview": _mask(runtime_config.apify_token()),
        },
    }


@router.put("")
def put_keys(body: KeysPatch):
    """Only updates fields actually provided; empty string clears a key."""
    patch: dict = {}
    for field, raw in body.model_dump().items():
        if raw is None:
            continue
        patch[field] = raw.strip() or None
    if patch:
        runtime_config.save(patch)
    return get_keys()


@router.post("/test/openai")
async def test_openai():
    k = runtime_config.openai_api_key()
    if not k:
        raise HTTPException(400, "OpenAI key not set")
    try:
        async with httpx.AsyncClient(timeout=10) as cx:
            r = await cx.get("https://api.openai.com/v1/models",
                             headers={"Authorization": f"Bearer {k}"})
        if r.status_code == 200:
            return {"ok": True}
        return {"ok": False, "status": r.status_code, "error": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@router.post("/test/tavily")
async def test_tavily():
    k = runtime_config.tavily_api_key()
    if not k:
        raise HTTPException(400, "Tavily key not set")
    try:
        async with httpx.AsyncClient(timeout=10) as cx:
            r = await cx.post("https://api.tavily.com/search",
                              json={"api_key": k, "query": "ping", "max_results": 1})
        if r.status_code == 200:
            return {"ok": True}
        return {"ok": False, "status": r.status_code, "error": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@router.post("/test/apify")
async def test_apify():
    k = runtime_config.apify_token()
    if not k:
        raise HTTPException(400, "Apify token not set")
    try:
        async with httpx.AsyncClient(timeout=10) as cx:
            r = await cx.get(f"https://api.apify.com/v2/users/me?token={k}")
        if r.status_code == 200:
            data = r.json().get("data", {})
            return {"ok": True, "username": data.get("username")}
        return {"ok": False, "status": r.status_code, "error": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
