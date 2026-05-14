"""SSE bus — per-run asyncio.Queue of events for the frontend stream.

Events shape: {event: "<type>", data: <json>}.
Types: agent.status, agent.tool, agent.token, agent.result, agent.error,
       gate.open, gate.resolved, run.complete.
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, AsyncIterator
from collections import defaultdict

# run_id -> list of subscriber queues
_subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
# run_id -> replay buffer (so a late connection can catch up)
_history: dict[str, list[dict]] = defaultdict(list)
# closed run_ids
_closed: set[str] = set()


async def publish(run_id: str, event: str, data: Any) -> None:
    payload = {"event": event, "data": data}
    _history[run_id].append(payload)
    for q in list(_subs.get(run_id, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def close(run_id: str) -> None:
    _closed.add(run_id)
    await publish(run_id, "run.complete", {"run_id": run_id})
    for q in list(_subs.get(run_id, [])):
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass


async def subscribe(run_id: str) -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subs[run_id].append(q)
    # replay history
    for evt in _history.get(run_id, []):
        yield {"event": evt["event"], "data": json.dumps(evt["data"])}
    if run_id in _closed:
        return
    try:
        while True:
            item = await q.get()
            if item is None:
                return
            yield {"event": item["event"], "data": json.dumps(item["data"])}
    finally:
        try:
            _subs[run_id].remove(q)
        except ValueError:
            pass


def history(run_id: str) -> list[dict]:
    return list(_history.get(run_id, []))
