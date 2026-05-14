"""Composio v3 HTTP client + Gmail draft/send.

We talk to Composio's documented v3 REST endpoints directly (no SDK):

  POST /api/v3/connected_accounts/link                  — initiate OAuth (returns redirect URL)
  GET  /api/v3/connected_accounts/{id}                  — poll connection status
  POST /api/v3/tools/execute/GMAIL_CREATE_EMAIL_DRAFT   — create draft
  POST /api/v3/tools/execute/GMAIL_SEND_EMAIL          — send

Pattern adapted from the sibling sdr-agent project's composio_client.py — same
shape, scoped down to the actions we need.
"""
from __future__ import annotations
import uuid
import asyncio
import httpx
from services import runtime_config

BASE = "https://backend.composio.dev"


def _headers() -> dict:
    key = runtime_config.composio_api_key()
    if not key:
        raise RuntimeError("Composio API key not set")
    return {"x-api-key": key, "Content-Type": "application/json"}


# ---------- Gmail connection lifecycle ----------

async def initiate_gmail(user_id: str, auth_config_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as cx:
        r = await cx.post(
            f"{BASE}/api/v3/connected_accounts/link",
            headers=_headers(),
            json={"auth_config_id": auth_config_id, "user_id": user_id},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
    return {
        "id": data.get("id") or data.get("connected_account_id"),
        "redirect_url": (data.get("redirect_url")
                         or data.get("redirectUrl")
                         or (data.get("connectionData") or {}).get("redirect_url")),
        "raw": data,
    }


async def get_connection_status(connection_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as cx:
        r = await cx.get(
            f"{BASE}/api/v3/connected_accounts/{connection_id}",
            headers=_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        data = r.json()
    return {"id": data.get("id", connection_id),
            "status": (data.get("status") or "").upper(),
            "raw": data}


# ---------- Draft / Send ----------

async def _execute_tool(slug: str, args: dict) -> dict:
    user_id = runtime_config.composio_entity_id()
    async with httpx.AsyncClient(timeout=30) as cx:
        r = await cx.post(
            f"{BASE}/api/v3/tools/execute/{slug}",
            headers=_headers(),
            json={"user_id": user_id, "arguments": args},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
        return r.json()


def _mock(recipient: str, subject: str) -> dict:
    return {
        "ok": True,
        "mode": "mock",
        "draft_id": f"mock-{uuid.uuid4().hex[:10]}",
        "thread_id": None,
        "message": f"Mock draft (no Composio key). To: {recipient}, Subject: {subject!r}.",
    }


async def create_draft(recipient: str, subject: str, body_html: str,
                       cc: str = "", bcc: str = "") -> dict:
    """Creates a Gmail draft in the user's connected Gmail account."""
    if not runtime_config.composio_api_key():
        return _mock(recipient, subject)
    args = {
        "recipient_email": recipient,
        "subject": subject,
        "body": body_html,
        "is_html": True,
    }
    if cc:
        args["cc"] = [c.strip() for c in cc.split(",") if c.strip()]
    if bcc:
        args["bcc"] = [b.strip() for b in bcc.split(",") if b.strip()]
    try:
        data = await _execute_tool("GMAIL_CREATE_EMAIL_DRAFT", args)
    except Exception as e:
        return {"ok": False, "mode": "error", "error": str(e)[:400]}
    inner = data.get("data") or data
    if isinstance(inner, dict):
        return {
            "ok": True, "mode": "real",
            "draft_id": (inner.get("id") or inner.get("draft_id")
                         or (inner.get("response_data") or {}).get("id") or "composio-draft"),
            "thread_id": inner.get("threadId") or (inner.get("response_data") or {}).get("threadId"),
            "raw": inner,
        }
    return {"ok": True, "mode": "real", "draft_id": "composio-draft", "raw": data}


# ---------- Status & ping helpers used by the UI ----------

async def gmail_overview(do_ping: bool = False) -> dict:
    """High-level status for the Settings page."""
    has_key = bool(runtime_config.composio_api_key())
    auth_cfg = runtime_config.composio_auth_config_id()
    conn_id = runtime_config.composio_connection_id() or runtime_config.composio_pending_connection_id()
    out = {
        "has_api_key": has_key,
        "has_auth_config": bool(auth_cfg),
        "auth_config_id_preview": _mask(auth_cfg),
        "entity_id": runtime_config.composio_entity_id(),
        "connection_id": conn_id or "",
        "connected": False,
        "status": "no_api_key" if not has_key
                  else "no_auth_config" if not auth_cfg
                  else "no_connection" if not conn_id else "unknown",
        "email": None,
    }
    if do_ping and has_key and conn_id:
        try:
            s = await get_connection_status(conn_id)
            raw_status = s.get("status") or ""
            out["status"] = raw_status
            out["connected"] = raw_status in ("ACTIVE", "CONNECTED", "AUTHORIZED", "SUCCESS", "SUCCESSFUL")
            # Composio sometimes returns email in nested fields — best-effort extract
            raw = s.get("raw") or {}
            out["email"] = (
                raw.get("emailAddress")
                or raw.get("user_email")
                or (raw.get("data") or {}).get("emailAddress")
                or (raw.get("user") or {}).get("emailAddress")
            )
            # promote pending → active once verified
            if out["connected"] and runtime_config.composio_pending_connection_id() and not runtime_config.composio_connection_id():
                runtime_config.save({
                    "composio_connection_id": runtime_config.composio_pending_connection_id(),
                    "composio_pending_connection_id": None,
                })
        except Exception as e:
            out["status"] = "error"
            out["error"] = str(e)[:300]
    return out


def _mask(s: str) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return "•" * len(s)
    return f"{s[:4]}…{s[-4:]}"
