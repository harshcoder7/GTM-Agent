"""Champion Scoring — Apify profile scrape → normalize → score."""
from __future__ import annotations
import asyncio
from pydantic import BaseModel, Field
from services import events, apify, llm
from agents._common import load_prompt, emit_start, emit_done


class ChampionScore(BaseModel):
    champion_score: int = Field(description="0-10")
    reasoning: str
    product_fit: str = Field(description="Echo of ICP's product_fit.")


def _normalize_profile(raw: dict) -> dict:
    """Handles both harvestapi and dev_fusion output shapes."""
    if not raw:
        return {}

    full_name = (raw.get("fullName") or raw.get("name") or
                 f"{raw.get('firstName','')} {raw.get('lastName','')}".strip())

    current_title = raw.get("jobTitle") or raw.get("currentJobTitle") or ""
    current_company = raw.get("companyName") or raw.get("company") or ""
    cur = raw.get("currentPosition") or []
    if isinstance(cur, list) and cur:
        c0 = cur[0] or {}
        current_title = current_title or c0.get("position", "")
        current_company = current_company or c0.get("companyName", "")

    loc = raw.get("addressWithCountry") or raw.get("location") or ""
    if isinstance(loc, dict):
        loc = loc.get("linkedinText") or loc.get("parsed", {}).get("text") or ""

    exp_raw = raw.get("experiences") or raw.get("experience") or []
    experience = []
    for e in exp_raw[:6]:
        if not isinstance(e, dict):
            continue
        title = e.get("title") or e.get("position") or ""
        company = e.get("companyName") or e.get("subtitle") or e.get("company") or ""
        duration = (e.get("caption") or e.get("dateRange") or
                    f"{(e.get('startDate') or {}).get('text','')} – {(e.get('endDate') or {}).get('text','present')}".strip(" –"))
        experience.append({"title": title, "company": company, "duration": duration})

    edu_raw = raw.get("educations") or raw.get("education") or []
    education = []
    for e in edu_raw[:4]:
        if not isinstance(e, dict):
            continue
        school = e.get("schoolName") or e.get("title") or ""
        degree = e.get("degree") or e.get("subtitle") or ""
        education.append({"school": school, "degree": degree})

    skills_raw = raw.get("topSkills") or raw.get("skills") or []
    if isinstance(skills_raw, list):
        skills = [s.get("name", s) if isinstance(s, dict) else s for s in skills_raw][:20]
    else:
        skills = []

    return {
        "full_name": full_name,
        "headline": raw.get("headline") or "",
        "current_title": current_title,
        "current_company": current_company,
        "location": loc,
        "about": (raw.get("about") or raw.get("summary") or "")[:1500],
        "experience": experience,
        "education": education,
        "skills": skills,
        "followers": raw.get("followerCount") or raw.get("followersCount") or raw.get("followers") or 0,
        "connections": raw.get("connectionsCount") or raw.get("connections") or 0,
    }


async def run(run_id: str, prospect: dict, icp: dict | None) -> dict:
    linkedin_url = prospect.get("linkedin_url") or prospect.get("Linkedin") or ""
    if not linkedin_url:
        started = await emit_start(run_id, "champion_scoring", "No LinkedIn URL — skipped")
        out = ChampionScore(champion_score=0, reasoning="No LinkedIn URL provided.",
                            product_fit=(icp or {}).get("product_fit", "Both")).model_dump()
        await emit_done(run_id, "champion_scoring", started, champion=out)
        return {"champion": out}

    started = await emit_start(run_id, "champion_scoring", "Scraping LinkedIn profile...")

    loop = asyncio.get_running_loop()
    def on_log(line: str) -> None:
        asyncio.run_coroutine_threadsafe(
            events.publish(run_id, "agent.tool",
                           {"agent": "champion_scoring", "phase": line, "kind": "log"}),
            loop,
        )

    try:
        raw = await apify.linkedin_profile(linkedin_url, on_log=on_log)
    except Exception as e:
        msg = str(e)[:300]
        print(f"[champion_scoring] Apify error: {msg}", flush=True)
        await events.publish(run_id, "agent.error", {"agent": "champion_scoring", "error": msg})
        raw = {}

    normalized = _normalize_profile(raw)
    await events.publish(run_id, "agent.tool",
                         {"agent": "champion_scoring",
                          "phase": f"Normalized profile · {normalized.get('current_title','?')} @ {normalized.get('current_company','?')} · followers={normalized.get('followers',0)}"})

    sys = load_prompt("champion_scoring.md")
    user = f"normalized_profile:\n{normalized}\n\nicp_profile:\n{icp or {}}"
    score = await llm.structured(sys, user, ChampionScore, temperature=0.2)
    out = score.model_dump()
    out["normalized_profile"] = normalized

    await emit_done(run_id, "champion_scoring", started, champion=out)
    return {"champion": out}
