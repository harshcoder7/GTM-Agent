from __future__ import annotations
import asyncio
import time
from pathlib import Path
from services import events
from services.container_logs import DeepResearchLogTailer

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


async def emit_start(run_id: str, agent: str, message: str) -> float:
    started = time.time()
    await events.publish(run_id, "agent.status", {
        "agent": agent, "state": "running", "message": message, "started_at": started,
    })
    return started


async def emit_done(run_id: str, agent: str, started: float, **extra) -> None:
    duration = round(time.time() - started, 2)
    payload = {"agent": agent, "duration_secs": duration, **extra}
    await events.publish(run_id, "agent.result", payload)


async def with_deep_research_logs(run_id: str, agent: str, coro):
    """Run `coro` while streaming the deep-research /logs/stream SSE feed
    into the agent's card as `agent.tool` log events.
    """
    def on_line(line: str) -> None:
        # We're inside the same event loop — schedule a non-blocking publish.
        asyncio.create_task(events.publish(run_id, "agent.tool", {
            "agent": agent, "phase": line, "kind": "log",
        }))

    tailer = DeepResearchLogTailer(on_line)
    tailer.start()
    # Tiny grace so the tailer subscribes before we trigger the work
    await asyncio.sleep(0.2)
    try:
        return await coro
    finally:
        await tailer.stop()
        await asyncio.sleep(0.3)
