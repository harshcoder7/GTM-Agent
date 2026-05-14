"""Lead Enrichment — calls deep-research /research, streams its container logs,
then OpenAI structured output."""
from __future__ import annotations
from pydantic import BaseModel, Field
from services import events, deep_research, llm
from agents._common import emit_start, emit_done, with_deep_research_logs


class EnrichedLead(BaseModel):
    company: str = Field(description="Company name, echoed.")
    overview: str = Field(description="1-2 paragraph overview from research.")
    size: str = Field(description="Employee count or range, e.g. 'Approximately 50 employees'.")
    revenue: str = Field(description="Revenue estimate, e.g. '$10M ARR' or 'NOT FOUND'.")
    domain: str
    funding_information: str = Field(description="Total raised + last round summary, or 'NOT FOUND'.")
    latest_funding_round: str = Field(description="Round name + date + amount.")
    investors: str = Field(description="Comma-separated investor names or 'NOT FOUND'.")
    linkedin_url: str = Field(description="Company LinkedIn URL, or 'NOT FOUND'.")
    sources: list[str] = Field(default_factory=list, description="List of URLs used as research sources.")


async def run(run_id: str, prospect: dict, *, cycles: int = 1) -> dict:
    company = prospect.get("company") or prospect.get("Company Name") or ""
    domain = prospect.get("domain") or prospect.get("Company Domain") or ""
    topic = f"Company firmographics + funding for: {company}. Domain: {domain}. Find size, revenue, total funding, latest round, investors, LinkedIn URL."

    started = await emit_start(run_id, "lead_enrichment", f"Researching {company} ({cycles}-cycle)...")

    research_resp = await with_deep_research_logs(
        run_id, "lead_enrichment", deep_research.research(topic, cycles=cycles),
    )
    final_report = research_resp.get("final_report", "") or ""
    raw_sources = research_resp.get("all_search_results", []) or []
    # Tavily results use `href`; some agents normalize to `url`. Accept both.
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
    source_urls = [c["url"] for c in citations]

    await events.publish(run_id, "agent.tool", {"agent": "lead_enrichment",
                                                "phase": f"Extracting 10 structured fields from a {len(final_report)}-char report"})

    system = ("You extract structured firmographic data from a research report. "
              "If a field is unknown, use 'NOT FOUND'. Return only what the schema requires.")
    user = f"Company: {company}\nDomain: {domain}\n\nRESEARCH REPORT:\n{final_report}\n\nKnown source URLs:\n" + "\n".join(source_urls[:15])
    enriched = await llm.structured(system, user, EnrichedLead)
    out = enriched.model_dump()

    await emit_done(run_id, "lead_enrichment", started,
                    enriched_lead=out, citations=citations[:20])
    return {
        "enriched_lead": out,
        "research_final_report": final_report,
        "research_sources": source_urls,
    }
