"""Apify thin wrapper — runs an actor synchronously and returns the dataset items.

Uses two actors:
  - harvestapi/linkedin-profile-posts  (recent posts for a profile URL)
  - dev_fusion/Linkedin-Profile-Scraper (full profile for champion scoring)
"""
from __future__ import annotations
import asyncio
from apify_client import ApifyClient
from config import settings
from services import runtime_config


def _client() -> ApifyClient:
    token = runtime_config.apify_token()
    if not token:
        raise RuntimeError("APIFY_TOKEN not configured (set it in /settings or .env)")
    return ApifyClient(token)


def _run_actor_sync(actor_id: str, run_input: dict, timeout_secs: int = 240,
                    on_log: callable | None = None) -> list[dict]:
    """Runs an actor and returns its dataset items.

    If `on_log` is provided, streams the actor's run log line-by-line via that callback.
    """
    client = _client()
    actor = client.actor(actor_id)
    # Start the run async-style so we can stream its log before it finishes.
    started = actor.start(run_input=run_input, timeout_secs=timeout_secs)
    run_id = started.get("id") if started else None
    if not run_id:
        return []
    run_client = client.run(run_id)
    if on_log:
        try:
            with run_client.log().stream() as resp:
                if resp:
                    for raw in resp.iter_lines():
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
                        try:
                            on_log(line.strip())
                        except Exception:
                            pass
        except Exception:
            pass
    final = run_client.wait_for_finish()
    if not final:
        return []
    dataset_id = final.get("defaultDatasetId")
    if not dataset_id:
        return []
    return list(client.dataset(dataset_id).iterate_items())


# Apify actor IDs (more reliable than slugs across permission flows).
# Override via .env (APIFY_POSTS_ACTOR, APIFY_PROFILE_ACTOR) — slugs work too.
PROFILE_ACTOR_ID = "2SyF0bVxmgGr8IVCZ"   # dev_fusion / Mass Linkedin Profile Scraper (Full permissions required)


async def linkedin_posts(profile_url: str, max_posts: int = 10,
                         on_log: callable | None = None) -> list[dict]:
    """harvestapi/linkedin-profile-posts — returns list of post dicts."""
    if not profile_url:
        return []
    run_input = {
        "targetUrls": [profile_url],
        "maxPosts": max_posts,
        "scrapeReactions": False,
        "scrapeComments": False,
    }
    return await asyncio.to_thread(_run_actor_sync, settings.apify_posts_actor, run_input, 240, on_log)


async def linkedin_profile(profile_url: str, on_log: callable | None = None) -> dict:
    """LinkedIn profile scrape for champion scoring — first profile dict (or {}).

    Defaults to `harvestapi/linkedin-profile-scraper` (free-tier, same vendor as the
    posts actor — uses `queries` for input). Falls back to env override.

    NOTE: `dev_fusion/Linkedin-Profile-Scraper` (actor 2SyF0bVxmgGr8IVCZ) is paid-tier
    only via API (free Apify plans can only run it through the UI), so we don't use it.
    """
    if not profile_url:
        return {}
    actor_id = settings.apify_profile_actor or "harvestapi/linkedin-profile-scraper"
    # If user left the old paid-only slug in env, swap to the free-tier harvestapi one.
    if actor_id.lower().endswith("/linkedin-profile-scraper") and "harvestapi" not in actor_id.lower():
        actor_id = "harvestapi/linkedin-profile-scraper"
    run_input = {
        "queries": [profile_url],
        "profileScraperMode": "Profile details no email ($4 per 1k)",
    }
    items = await asyncio.to_thread(_run_actor_sync, actor_id, run_input, 240, on_log)
    return items[0] if items else {}
