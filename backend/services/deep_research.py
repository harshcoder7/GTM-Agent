"""Async httpx client for the deep-research-agent FastAPI sidecar (port 8771).

Endpoints used:
  POST /research  → firmographic + funding facts (lead enrichment backbone)
  POST /signals   → recent product/news/social signals (market intelligence backbone)

Both return: {topic, final_report, final_summary, all_search_results, usage_summary, research_cycles_completed}
"""
from __future__ import annotations
import httpx
from config import settings
from services import runtime_config


async def _call(endpoint: str, topic: str, cycles: int) -> dict:
    payload = {
        "topic": topic,
        "cycles": cycles,
        "tavily_api_key": runtime_config.tavily_api_key(),
        "openai_api_key": runtime_config.openai_api_key(),
        "openai_model": settings.openai_fast_model,
        # Fast-mode caps — keep deep-research snappy for the live demo.
        "max_search_results_per_query": 4,
        "max_urls_to_scrape_per_cycle": 2,
    }
    async with httpx.AsyncClient(timeout=600) as cx:
        r = await cx.post(f"{settings.deep_research_url.rstrip('/')}/{endpoint}", json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"deep-research {endpoint} HTTP {r.status_code}: {r.text[:400]}")
        return r.json()


async def research(topic: str, cycles: int | None = None) -> dict:
    return await _call("research", topic, cycles or settings.deep_research_cycles)


async def signals(topic: str, cycles: int | None = None) -> dict:
    return await _call("signals", topic, cycles or settings.deep_research_cycles)


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as cx:
            r = await cx.get(f"{settings.deep_research_url.rstrip('/')}/health")
            return r.status_code == 200
    except Exception:
        return False
