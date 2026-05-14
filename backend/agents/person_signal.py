"""Person LinkedIn Signal — Apify harvestapi/linkedin-profile-posts → engagement summary."""
from __future__ import annotations
import asyncio
from pydantic import BaseModel, Field
from services import events, apify, llm
from agents._common import load_prompt, emit_start, emit_done


class PersonSignal(BaseModel):
    person_name: str
    core_themes: list[str] = Field(default_factory=list)
    writing_style: str = ""
    recent_focus: str = ""
    engagement_trend: str = ""
    best_personalization_angle: str = ""
    example_opening_line: str = ""
    signal_strength: str = Field(default="weak", description="strong | medium | weak")


def _normalize_posts(items: list[dict]) -> str:
    if not items:
        return ""
    out = []
    for i, p in enumerate(items[:15], 1):
        text = (p.get("text") or p.get("content") or p.get("postText") or p.get("commentary") or "").strip()
        if not text:
            continue
        reactions = p.get("reactions") or p.get("numLikes") or p.get("likesCount") or ""
        out.append(f"--- Post {i} (reactions: {reactions}) ---\n{text[:1200]}")
    return "\n\n".join(out)


async def run(run_id: str, prospect: dict) -> dict:
    linkedin_url = prospect.get("linkedin_url") or prospect.get("Linkedin") or ""
    person_name = prospect.get("full_name") or prospect.get("Name") or ""

    if not linkedin_url:
        weak = PersonSignal(person_name=person_name, signal_strength="weak",
                            recent_focus="No LinkedIn URL provided.").model_dump()
        started = await emit_start(run_id, "person_signal", "No LinkedIn URL — skipped")
        await emit_done(run_id, "person_signal", started, person_signal=weak)
        return {"person_signal": weak}

    started = await emit_start(run_id, "person_signal", f"Scraping recent posts for {person_name}...")

    loop = asyncio.get_running_loop()
    def on_log(line: str) -> None:
        asyncio.run_coroutine_threadsafe(
            events.publish(run_id, "agent.tool",
                           {"agent": "person_signal", "phase": line, "kind": "log"}),
            loop,
        )

    try:
        items = await apify.linkedin_posts(linkedin_url, max_posts=10, on_log=on_log)
    except Exception as e:
        msg = str(e)[:300]
        print(f"[person_signal] Apify error: {msg}", flush=True)
        await events.publish(run_id, "agent.error", {"agent": "person_signal", "error": msg})
        items = []

    posts_text = _normalize_posts(items)
    await events.publish(run_id, "agent.tool",
                         {"agent": "person_signal", "phase": f"Got {len(items)} post(s)"})

    if not posts_text:
        weak = PersonSignal(person_name=person_name, signal_strength="weak",
                            recent_focus="No recent LinkedIn posts available.",
                            best_personalization_angle="Fall back to company-level personalization.").model_dump()
        await emit_done(run_id, "person_signal", started, person_signal=weak)
        return {"person_signal": weak}

    sys = load_prompt("person_signal.md")
    user = f"Person name: {person_name}\nLinkedIn URL: {linkedin_url}\n\nRecent posts:\n\n{posts_text}"
    sig = await llm.structured(sys, user, PersonSignal, temperature=0.3)
    out = sig.model_dump()
    if not out.get("person_name"):
        out["person_name"] = person_name

    await emit_done(run_id, "person_signal", started, person_signal=out)
    return {"person_signal": out}
