"""Subscribes to the deep-research sidecar's /logs/stream SSE feed and forwards
each log event to a callback. Used to surface the engine's internal research
log (Tavily queries, scraping, reflection) inside our agent cards.

No host privileges required — pure HTTP between containers on the compose net.
"""
from __future__ import annotations
import asyncio
import json
import re
from typing import Callable, Optional
import httpx
from config import settings

_FLAGS = re.MULTILINE
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,\d]*Z?\s*", _FLAGS)


def _clean(line: str) -> str:
    # Drop ISO timestamp prefix that's already in the meta
    return _TS_RE.sub("", line).strip()


class DeepResearchLogTailer:
    """Streams the deep-research /logs/stream SSE endpoint and calls `on_line`."""

    def __init__(self, on_line: Callable[[str], None], *, base_url: Optional[str] = None):
        self.on_line = on_line
        self.base_url = (base_url or settings.deep_research_url).rstrip("/")
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="deep-research-log-tailer")

    async def _run(self) -> None:
        url = f"{self.base_url}/logs/stream"
        try:
            async with httpx.AsyncClient(timeout=None) as cx:
                async with cx.stream("GET", url, headers={"Accept": "text/event-stream"}) as resp:
                    if resp.status_code != 200:
                        self._safe(f"[log tailer: {url} → HTTP {resp.status_code}]")
                        return
                    buf = ""
                    async for chunk in resp.aiter_text():
                        if self._stop.is_set():
                            return
                        buf += chunk
                        # Split SSE events by blank line
                        while "\n\n" in buf:
                            block, buf = buf.split("\n\n", 1)
                            self._handle_block(block)
        except (asyncio.CancelledError, Exception) as e:  # noqa: BLE001
            if not isinstance(e, asyncio.CancelledError):
                self._safe(f"[log tailer ended: {e!s}]")

    def _handle_block(self, block: str) -> None:
        # Parse SSE block: lines starting with "data:"
        for line in block.split("\n"):
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            try:
                obj = json.loads(data)
                raw = obj.get("line", "")
            except Exception:
                raw = data
            cleaned = _clean(raw)
            if cleaned:
                self._safe(cleaned)

    def _safe(self, line: str) -> None:
        try:
            self.on_line(line)
        except Exception:
            pass

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
