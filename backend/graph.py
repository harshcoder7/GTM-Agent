"""Orchestrator — runs the 6-agent pipeline as a single asyncio task,
pausing at Gate 1 (after Drafting) for human review. State persists in the DB.

Why not LangGraph here: the human pause spans HTTP request boundaries (rep
reviews in the UI, then POSTs /review). Asyncio + DB-as-state is simpler and
gives us tight control over per-agent SSE timing.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from db import models
from db.session import SessionLocal
from services import events, deep_research as dr_client
from agents import (lead_enrichment, market_intelligence, icp_profiling,
                    person_signal, champion_scoring, drafting)


def _save_citations(db: Session, run_id: str, agent: str, urls: list[str]) -> None:
    for url in urls[:30]:
        if url:
            db.add(models.Citation(run_id=run_id, agent=agent, url=url))


def _persist_history(db: Session, run_id: str) -> None:
    """Snapshot the in-memory SSE history onto the Run row so a later page
    load can replay every agent's status / tool lines / result."""
    row = db.get(models.Run, run_id)
    if not row:
        return
    row.events_history = events.history(run_id)
    db.commit()


async def run_pipeline(run_id: str, force_placeholder: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        run_row = db.get(models.Run, run_id)
        if not run_row:
            return
        prospect = run_row.prospect_json

        await events.publish(run_id, "agent.status",
                             {"agent": "system", "state": "running",
                              "message": f"Pipeline starting for {prospect.get('full_name','prospect')} · {prospect.get('company','')}"})

        cycles = max(1, min(3, int(getattr(run_row, "research_cycles", 1) or 1)))

        # 1. Lead Enrichment
        run_row.status = "enriching"; db.commit()
        le_out = await lead_enrichment.run(run_id, prospect, cycles=cycles)
        run_row.enriched_lead = le_out["enriched_lead"]
        _save_citations(db, run_id, "lead_enrichment", le_out.get("research_sources", []))
        db.commit()

        # 2. Market Intelligence  (parallel-friendly but kept sequential for UI clarity)
        run_row.status = "market"; db.commit()
        mi_out = await market_intelligence.run(run_id, prospect, run_row.enriched_lead, cycles=cycles)
        run_row.market_intel = mi_out["market_intel"]
        _save_citations(db, run_id, "market_intelligence", mi_out.get("market_sources", []))
        db.commit()

        # 3. ICP Profiling
        run_row.status = "icp"; db.commit()
        icp_out = await icp_profiling.run(run_id, prospect, run_row.enriched_lead, run_row.market_intel)
        run_row.icp = icp_out["icp"]
        run_row.icp_score = icp_out["icp"].get("icp_score")
        run_row.route_decision = icp_out["route_decision"]
        run_row.product_fit = icp_out["product_fit"]
        db.commit()

        if icp_out["route_decision"] == "escalate":
            run_row.status = "escalated"
            run_row.escalation_reason = f"ICP score {run_row.icp_score} < 5 — refusing to draft."
            db.commit()
            await events.publish(run_id, "agent.status",
                                 {"agent": "system", "state": "running",
                                  "message": "ICP scored cold — refusing to draft. Pipeline complete."})
            _persist_history(db, run_id)
            await events.close(run_id)
            return

        # 4. Person LinkedIn Signal
        run_row.status = "person"; db.commit()
        ps_out = await person_signal.run(run_id, prospect)
        run_row.person_signal = ps_out["person_signal"]
        db.commit()

        # 5. Champion Scoring
        run_row.status = "champion"; db.commit()
        cs_out = await champion_scoring.run(run_id, prospect, run_row.icp)
        run_row.champion = cs_out["champion"]
        db.commit()

        # 6. Drafting → opens Gate 1
        run_row.status = "drafting"; db.commit()
        dr_out = await drafting.run(
            run_id, prospect, run_row.enriched_lead, run_row.icp,
            run_row.market_intel, run_row.person_signal, run_row.champion,
            force_placeholder=force_placeholder,
        )
        draft = dr_out["draft"]
        # persist Draft row
        d_row = models.Draft(
            run_id=run_id, version=1,
            subject=draft.get("subject", ""), greeting=draft.get("greeting", ""),
            introduction=draft.get("introduction", ""), pain_point=draft.get("pain_point", ""),
            product_desc=draft.get("product_desc", ""), bullet_points=draft.get("bullet_points", []),
            cta=draft.get("cta", ""), html=draft.get("html", ""), approved_by_human=False,
        )
        db.add(d_row)
        run_row.status = "awaiting_review"
        run_row.product_fit = dr_out.get("product_fit") or run_row.product_fit
        db.commit()

        await events.publish(run_id, "gate.open",
                             {"gate": "review", "run_id": run_id, "draft_id": d_row.id})
        _persist_history(db, run_id)
        # do NOT close SSE — rep will act via /review

    except Exception as e:
        await events.publish(run_id, "agent.error",
                             {"agent": "system", "error": f"Pipeline error: {e}"})
        try:
            run_row = db.get(models.Run, run_id)
            if run_row:
                run_row.status = "error"
                run_row.escalation_reason = f"error: {e}"
                db.commit()
            _persist_history(db, run_id)
        finally:
            await events.close(run_id)
    finally:
        db.close()


def fire_and_forget(run_id: str, force_placeholder: bool = False) -> None:
    asyncio.create_task(run_pipeline(run_id, force_placeholder))


async def regenerate_draft(run_id: str, steering_note: str | None = None) -> None:
    """Re-runs only the drafting node with current state. Triggered by Gate 1 'regenerate'."""
    db: Session = SessionLocal()
    try:
        run_row = db.get(models.Run, run_id)
        if not run_row:
            return
        run_row.status = "drafting"; db.commit()
        prospect = dict(run_row.prospect_json)
        if steering_note:
            prospect["_steering_note"] = steering_note
        dr_out = await drafting.run(
            run_id, prospect, run_row.enriched_lead or {}, run_row.icp or {},
            run_row.market_intel, run_row.person_signal, run_row.champion,
            force_placeholder=run_row.force_placeholder,
        )
        draft = dr_out["draft"]
        last_v = db.query(models.Draft).filter_by(run_id=run_id).count()
        d_row = models.Draft(
            run_id=run_id, version=last_v + 1,
            subject=draft.get("subject", ""), greeting=draft.get("greeting", ""),
            introduction=draft.get("introduction", ""), pain_point=draft.get("pain_point", ""),
            product_desc=draft.get("product_desc", ""), bullet_points=draft.get("bullet_points", []),
            cta=draft.get("cta", ""), html=draft.get("html", ""), approved_by_human=False,
        )
        db.add(d_row)
        run_row.status = "awaiting_review"; db.commit()
        await events.publish(run_id, "gate.open", {"gate": "review", "run_id": run_id, "draft_id": d_row.id})
        _persist_history(db, run_id)
    finally:
        db.close()
