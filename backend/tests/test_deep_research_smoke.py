"""Smoke test the deep-research sidecar. Skipped if the service is not reachable."""
import os
import pytest
import httpx
from config import settings


@pytest.mark.asyncio
async def test_health():
    url = settings.deep_research_url
    try:
        async with httpx.AsyncClient(timeout=3) as cx:
            r = await cx.get(f"{url}/health")
    except Exception:
        pytest.skip(f"deep-research not reachable at {url}")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"
