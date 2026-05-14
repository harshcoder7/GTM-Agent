"""Composio + Gmail UI flow.

Endpoints used by the Settings page:

  PUT  /api/composio/api-key         — store Composio API key
  PUT  /api/composio/auth-config     — store Gmail auth_config_id (created in Composio dashboard)
  POST /api/composio/gmail/connect   — initiate Gmail OAuth → returns redirect URL
  GET  /api/composio/gmail/status    — current connection state (+ live ping)
  POST /api/composio/gmail/disconnect — clear connection
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import runtime_config, composio_gmail

router = APIRouter(prefix="/api/composio", tags=["composio"])


class ApiKeyBody(BaseModel):
    api_key: str


class AuthConfigBody(BaseModel):
    auth_config_id: str


class ConnectBody(BaseModel):
    entity_id: str | None = "default"


@router.put("/api-key")
def set_api_key(body: ApiKeyBody):
    key = (body.api_key or "").strip()
    if not key:
        raise HTTPException(400, "api_key required")
    runtime_config.set_value("composio_api_key", key)
    return {"ok": True}


@router.put("/auth-config")
def set_auth_config(body: AuthConfigBody):
    v = (body.auth_config_id or "").strip()
    if not v:
        raise HTTPException(400, "auth_config_id required")
    runtime_config.set_value("composio_gmail_auth_config", v)
    return {"ok": True}


@router.post("/gmail/connect")
async def connect_gmail(body: ConnectBody):
    if not runtime_config.composio_api_key():
        raise HTTPException(400, "Set Composio API key first.")
    auth_cfg = runtime_config.composio_auth_config_id()
    if not auth_cfg:
        raise HTTPException(400, "Set the Gmail auth_config_id first "
                                  "(create one in Composio dashboard → Auth Configs).")
    entity = (body.entity_id or "default").strip() or "default"
    runtime_config.set_value("composio_entity_id", entity)
    try:
        out = await composio_gmail.initiate_gmail(entity, auth_cfg)
    except Exception as e:
        raise HTTPException(400, f"Composio initiate failed: {e}")
    if not out.get("redirect_url") or not out.get("id"):
        raise HTTPException(500, f"Composio returned unexpected response: {out.get('raw')}")
    runtime_config.set_value("composio_pending_connection_id", out["id"])
    return {"redirect_url": out["redirect_url"], "connection_id": out["id"]}


@router.get("/gmail/status")
async def gmail_status(ping: bool = False):
    """Returns Composio/Gmail status. Skips the live Composio ping by default
    (it adds ~700ms). Pass ?ping=1 from the UI's Re-check button to verify."""
    return await composio_gmail.gmail_overview(do_ping=ping)


@router.post("/gmail/disconnect")
def disconnect():
    runtime_config.save({
        "composio_connection_id": None,
        "composio_pending_connection_id": None,
    })
    return {"ok": True}
