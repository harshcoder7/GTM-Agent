"""Market Intelligence — calls deep-research /signals, streams its container logs,
then OpenAI structured output."""
from __future__ import annotations
from pydantic import BaseModel, Field
from services import events, deep_research, llm
from agents._common import emit_start, emit_done, with_deep_research_logs


class MarketIntel(BaseModel):
    industry: str = Field(description="Sector or vertical.")
    customer_segments: str = Field(description="Key buyer personas or end customers.")
    business_model: str = Field(description="How they make money.")
    geographic_presence: str = Field(description="Regions or countries.")
    product_launches: str = Field(description="Recent product launches with names + dates.")
    press_pr: str = Field(description="Recent press / announcements / features.")
    social_media_activity: str = Field(description="Notable tweets, LinkedIn posts, executive interviews.")


async def run(run_id: str, prospect: dict, enriched_lead: dict | None, *, cycles: int = 1) -> dict:
    company = prospect.get("company") or (enriched_lead or {}).get("company") or ""
    domain = prospect.get("domain") or (enriched_lead or {}).get("domain") or ""
    topic = (f"Recent market intelligence signals for {company} ({domain}): "
             f"product launches, press, PR, executive interviews, social posts, hiring announcements.")

    started = await emit_start(run_id, "market_intelligence", f"Pulling recent signals for {company} ({cycles}-cycle)...")

    resp = await with_deep_research_logs(
        run_id, "market_intelligence", deep_research.signals(topic, cycles=cycles),
    )
    final_report = resp.get("final_report", "") or ""
    raw_sources = resp.get("all_search_results", []) or []
    def _url(s: dict) -> str:
        return s.get("url") or s.get("href") or ""
    seen: set[str] = set()
    citations: list[dict] = []
    for s in raw_sources:
        if not isinstance(s, dict):
            continue
        u = _url(s)
        if not u or u in seen:
            continue
        seen.add(u)
        citations.append({"url": u, "title": s.get("title", "")})
    sources = [c["url"] for c in citations]

    system = "You extract structured market intelligence from a research report. Be concise."
    user = f"Company: {company}\n\nSIGNALS REPORT:\n{final_report}"
    intel = await llm.structured(system, user, MarketIntel)
    out = intel.model_dump()

    await emit_done(run_id, "market_intelligence", started,
                    market_intel=out, citations=citations[:20])
    return {
        "market_intel": out,
        "market_sources": sources,
        "market_final_report": final_report,
    }
