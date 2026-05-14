from __future__ import annotations
import uuid
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from db.session import get_db
from db import models
from services import events, email_render, safety, composio_gmail
from graph import fire_and_forget, regenerate_draft

router = APIRouter(prefix="/api/runs", tags=["runs"])


class Prospect(BaseModel):
    full_name: str
    company: str
    linkedin_url: Optional[str] = ""
    job_title: Optional[str] = ""
    email: Optional[str] = ""
    domain: Optional[str] = ""


class CreateRunBody(BaseModel):
    prospect: Prospect
    bulk_id: Optional[str] = None
    force_placeholder: Optional[bool] = False
    research_cycles: Optional[int] = 1  # 1-3 inclusive — number of deep-research cycles


class ReviewDecision(BaseModel):
    decision: str = Field(description="approve | edit_approve | regenerate | reject")
    edits: Optional[dict] = None
    steering_note: Optional[str] = None


@router.post("")
async def create_run(body: CreateRunBody, db: Session = Depends(get_db)):
    rid = uuid.uuid4().hex[:12]
    cycles = max(1, min(3, int(body.research_cycles or 1)))
    row = models.Run(
        id=rid,
        prospect_json=body.prospect.model_dump(),
        bulk_id=body.bulk_id,
        force_placeholder=bool(body.force_placeholder),
        research_cycles=cycles,
        status="queued",
    )
    db.add(row); db.commit()
    fire_and_forget(rid, force_placeholder=bool(body.force_placeholder))
    return {"run_id": rid, "research_cycles": cycles}


@router.get("/{run_id}/stream")
async def stream(run_id: str):
    async def gen():
        async for evt in events.subscribe(run_id):
            yield evt
    return EventSourceResponse(gen())


@router.get("")
def list_runs(db: Session = Depends(get_db), limit: int = 100):
    rows = db.query(models.Run).order_by(models.Run.created_at.desc()).limit(limit).all()
    return [{
        "id": r.id, "created_at": r.created_at.isoformat() if r.created_at else None,
        "status": r.status, "icp_score": r.icp_score, "product_fit": r.product_fit,
        "prospect": r.prospect_json, "drafted_at": r.drafted_at.isoformat() if r.drafted_at else None,
        "bulk_id": r.bulk_id, "route_decision": r.route_decision,
    } for r in rows]


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    r = db.get(models.Run, run_id)
    if not r:
        raise HTTPException(404)
    drafts = db.query(models.Draft).filter_by(run_id=run_id).order_by(models.Draft.version).all()
    citations = db.query(models.Citation).filter_by(run_id=run_id).all()
    safeties = db.query(models.SafetyCheck).filter_by(run_id=run_id).all()
    return {
        "id": r.id,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "prospect": r.prospect_json,
        "enriched_lead": r.enriched_lead,
        "market_intel": r.market_intel,
        "icp": r.icp,
        "person_signal": r.person_signal,
        "champion": r.champion,
        "icp_score": r.icp_score,
        "route_decision": r.route_decision,
        "product_fit": r.product_fit,
        "escalation_reason": r.escalation_reason,
        "drafted_at": r.drafted_at.isoformat() if r.drafted_at else None,
        "composio_draft_id": r.composio_draft_id,
        "drafts": [{"id": d.id, "version": d.version, "subject": d.subject, "greeting": d.greeting,
                    "introduction": d.introduction, "pain_point": d.pain_point,
                    "product_desc": d.product_desc, "bullet_points": d.bullet_points,
                    "cta": d.cta, "html": d.html, "approved": d.approved_by_human}
                   for d in drafts],
        "citations": [{"agent": c.agent, "url": c.url, "title": c.title} for c in citations],
        "safety_checks": [{"check": s.check_name, "passed": s.passed, "explanation": s.explanation}
                          for s in safeties],
        # Persisted SSE history — present for terminal runs so the page can
        # replay every agent's logs, citations and durations.
        "events_history": r.events_history or [],
    }


@router.get("/{run_id}/history")
def get_history(run_id: str):
    """Replay buffer for the SSE stream — useful for debugging / late connections."""
    return {"events": events.history(run_id)}


@router.get("/{run_id}/safety")
def get_safety(run_id: str, db: Session = Depends(get_db)):
    r = db.get(models.Run, run_id)
    if not r:
        raise HTTPException(404)
    draft_row = db.query(models.Draft).filter_by(run_id=run_id).order_by(models.Draft.version.desc()).first()
    if not draft_row:
        return {"checks": []}
    draft = {"subject": draft_row.subject, "greeting": draft_row.greeting,
             "introduction": draft_row.introduction, "pain_point": draft_row.pain_point,
             "product_desc": draft_row.product_desc, "bullet_points": draft_row.bullet_points,
             "cta": draft_row.cta}
    recipient = r.prospect_json.get("email") if r.prospect_json else None
    checks = safety.run_all(draft, r.icp, r.product_fit, recipient)
    return {"checks": checks, "all_passed": all(c["passed"] for c in checks)}


@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    r = db.get(models.Run, run_id)
    if not r:
        raise HTTPException(404)
    # Cascade deletes drafts/citations/safety_checks via the relationship config.
    db.delete(r)
    db.commit()
    # Clean up any in-memory SSE state for this run too
    events._subs.pop(run_id, None)
    events._history.pop(run_id, None)
    events._closed.discard(run_id)
    return {"ok": True, "deleted": run_id}


@router.delete("")
def delete_all_runs(db: Session = Depends(get_db)):
    n = db.query(models.Run).count()
    # Children are deleted via cascade on the Run rows.
    db.query(models.SafetyCheck).delete()
    db.query(models.Citation).delete()
    db.query(models.Draft).delete()
    db.query(models.Run).delete()
    db.commit()
    events._subs.clear()
    events._history.clear()
    events._closed.clear()
    return {"ok": True, "deleted": n}


@router.post("/{run_id}/review")
async def review(run_id: str, body: ReviewDecision, db: Session = Depends(get_db)):
    r = db.get(models.Run, run_id)
    if not r:
        raise HTTPException(404)
    if r.status not in ("awaiting_review",):
        raise HTTPException(409, f"Run not awaiting review (status={r.status})")

    draft_row = db.query(models.Draft).filter_by(run_id=run_id).order_by(models.Draft.version.desc()).first()

    if body.decision in ("approve", "edit_approve"):
        if body.decision == "edit_approve" and body.edits and draft_row:
            for field in ("subject", "greeting", "introduction", "pain_point", "product_desc", "cta"):
                if field in body.edits:
                    setattr(draft_row, field, body.edits[field])
            if "bullet_points" in body.edits:
                draft_row.bullet_points = body.edits["bullet_points"]
            # re-render HTML on edits
            d_dict = {f: getattr(draft_row, f) for f in
                      ("subject", "greeting", "introduction", "pain_point", "product_desc",
                       "bullet_points", "cta")}
            draft_row.html = email_render.render_email_html(d_dict, r.product_fit)

        # run safety
        d_dict = {f: getattr(draft_row, f) for f in
                  ("subject", "greeting", "introduction", "pain_point", "product_desc",
                   "bullet_points", "cta")}
        recipient = r.prospect_json.get("email") if r.prospect_json else None
        checks = safety.run_all(d_dict, r.icp, r.product_fit, recipient)
        # persist
        db.query(models.SafetyCheck).filter_by(run_id=run_id).delete()
        for c in checks:
            db.add(models.SafetyCheck(run_id=run_id, check_name=c["check"],
                                      passed=c["passed"], explanation=c["explanation"]))
        db.commit()
        if not all(c["passed"] for c in checks):
            failed = [c for c in checks if not c["passed"]]
            await events.publish(run_id, "gate.resolved",
                                 {"gate": "review", "decision": "blocked",
                                  "failed_checks": failed})
            return {"status": r.status, "blocked": True, "failed_checks": failed}

        # Create Gmail draft via Composio
        await events.publish(run_id, "agent.status",
                             {"agent": "composio", "state": "running",
                              "message": "Creating Gmail draft..."})
        result = await composio_gmail.create_draft(
            recipient=recipient or "",
            subject=draft_row.subject,
            body_html=draft_row.html,
        )
        if result.get("ok"):
            draft_row.approved_by_human = True
            r.composio_draft_id = result.get("draft_id")
            r.composio_thread_id = result.get("thread_id")
            r.drafted_at = datetime.utcnow()
            r.status = "drafted"
            db.commit()
            await events.publish(run_id, "gate.resolved",
                                 {"gate": "review", "decision": "approve",
                                  "draft_id": result.get("draft_id"), "mode": result.get("mode")})
            # persist final history snapshot for past-run replay
            r.events_history = events.history(run_id); db.commit()
            await events.close(run_id)
            return {"status": r.status, "draft_id": result.get("draft_id"), "mode": result.get("mode")}
        else:
            await events.publish(run_id, "agent.error",
                                 {"agent": "composio", "error": result.get("error", "unknown")})
            return {"status": r.status, "error": result.get("error")}

    if body.decision == "reject":
        r.status = "rejected"; db.commit()
        await events.publish(run_id, "gate.resolved", {"gate": "review", "decision": "reject"})
        r.events_history = events.history(run_id); db.commit()
        await events.close(run_id)
        return {"status": r.status}

    if body.decision == "regenerate":
        await events.publish(run_id, "gate.resolved",
                             {"gate": "review", "decision": "regenerate"})
        asyncio.create_task(regenerate_draft(run_id, body.steering_note))
        return {"status": "drafting", "regenerating": True}

    raise HTTPException(400, "unknown decision")
