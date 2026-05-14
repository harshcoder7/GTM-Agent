"""Drafting — assemble all upstream context and produce the final email JSON.

Renders HTML via services/email_render. Persists Draft row. Opens Gate 1.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from services import events, llm, brain, email_render
from agents._common import load_prompt, emit_start, emit_done


class EmailDraft(BaseModel):
    subject: str
    greeting: str
    introduction: str
    pain_point: str
    product_desc: str
    bullet_points: list[str] = Field(default_factory=list)
    cta: str


def _channel_label() -> str:
    return "Gmail"


async def run(run_id: str, prospect: dict, enriched_lead: dict, icp: dict,
              market_intel: dict | None, person_signal: dict | None,
              champion: dict | None, *, force_placeholder: bool = False) -> dict:
    started = await emit_start(run_id, "drafting", "Composing personalised email...")

    sender = brain.sender_block()
    sys = load_prompt("drafting.md")
    user = (
        f"CONTACT_INFO:\nName: {prospect.get('full_name','')}\nTitle: {prospect.get('job_title','')}\n"
        f"Company: {prospect.get('company','')}\nEmail: {prospect.get('email','')}\nLinkedIn: {prospect.get('linkedin_url','')}\n\n"
        f"COMPANY_INFO:\n{enriched_lead}\n\n"
        f"ICP_ASSESSMENT:\n{icp}\n\n"
        f"MARKET_INTELLIGENCE:\n{market_intel or '(not available)'}\n\n"
        f"PRODUCT_CONTEXT:\n{brain.product_context_block()}\n\n"
        f"PREFERRED_TONE: {brain.load_brain().get('preferred_tone','warm, consultative')}\n\n"
        f"LINKEDIN_ENGAGEMENT_SIGNAL:\n{person_signal or '(not available)'}\n\n"
        f"CHAMPION_SCORE:\n{champion or '(not available)'}\n\n"
        f"Sender: {sender.get('sender_name','')} ({sender.get('sender_title','')}) at {sender.get('name','')}\n"
        f"Channel: {_channel_label()}"
    )

    draft = await llm.structured(sys, user, EmailDraft, temperature=0.6)
    d = draft.model_dump()

    if force_placeholder:
        d["introduction"] = d["introduction"] + " Quick note from {{first_name}} —"
        await events.publish(run_id, "agent.tool", {"agent": "drafting",
                                                    "phase": "DEMO: injected placeholder leak for Gate 1 safety test"})

    product_fit = icp.get("product_fit") if icp else None
    html = email_render.render_email_html(d, product_fit)
    d["html"] = html

    await emit_done(run_id, "drafting", started, draft=d, product_fit=product_fit)
    return {"draft": d, "product_fit": product_fit}
