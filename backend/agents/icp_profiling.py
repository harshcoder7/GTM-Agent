"""ICP Profiling — scrape company site, summarize their offerings, then score.

Two LLM passes:
  1. Product summary from scraped site (fast model)
  2. ICP scoring combining enriched_lead + market_intel + product_summary + seller context + target ICP (reasoning model)
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from services import events, llm, web_scraper, brain
from agents._common import load_prompt, emit_start, emit_done


class ICPProfile(BaseModel):
    product_fit: str = Field(description='One of: "Pro", "Hive", "Both"')
    icp_score: float = Field(description="Score 1-10")
    prospect_level: str = Field(description="High | Mid | Low")
    engagement_readiness: str = Field(description="Hot | Warm | Cold")
    justification: str = Field(description="Reasoning grounded in exact phrases from the lead's data.")
    use_case: str = Field(description="1-2 sentences: how our product applies, with micro-scenario.")


async def run(run_id: str, prospect: dict, enriched_lead: dict, market_intel: dict | None) -> dict:
    domain = (enriched_lead or {}).get("domain") or prospect.get("domain") or ""
    company = (enriched_lead or {}).get("company") or prospect.get("company") or ""

    started = await emit_start(run_id, "icp_profiling", f"Scraping {domain or 'n/a'} for product offerings...")

    site_text = await web_scraper.scrape_site(domain) if domain else ""
    await events.publish(run_id, "agent.tool", {"agent": "icp_profiling",
                                                "phase": f"Scraped {len(site_text)} chars from {domain or 'n/a'}"})

    # Pass 1 — product summary
    product_summary = ""
    if site_text:
        sys1 = load_prompt("icp_product_summary.md")
        user1 = f"Scraped website content for {company}:\n\n{site_text}"
        product_summary = await llm.chat(sys1, user1, temperature=0.2)
        await events.publish(run_id, "agent.tool", {"agent": "icp_profiling", "phase": "Built product summary"})
    else:
        product_summary = f"(no scraped content available for {company})"

    # Pass 2 — ICP scoring
    sys2 = load_prompt("icp_scoring.md").format(
        product_context=brain.product_context_block(),
        target_icp=brain.target_icp(),
    )
    user2 = (
        f"## Enriched lead\n{enriched_lead}\n\n"
        f"## Market intelligence\n{market_intel or '(not available)'}\n\n"
        f"## Their products & offerings (from scraping their site)\n{product_summary}"
    )
    profile = await llm.structured(sys2, user2, ICPProfile, model=None, temperature=0.2)
    out = profile.model_dump()
    out["product_summary"] = product_summary

    route = "draft" if out["icp_score"] >= 5 else "escalate"
    out["route_decision"] = route

    await emit_done(run_id, "icp_profiling", started, icp=out, route=route)
    return {"icp": out, "route_decision": route, "product_fit": out["product_fit"]}
