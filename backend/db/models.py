from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.session import Base


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    # queued | enriching | market | icp | person | champion | drafting | awaiting_review | drafted | sent | rejected | escalated | error

    prospect_json: Mapped[dict] = mapped_column(JSON)
    enriched_lead: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    market_intel: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    icp: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    person_signal: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    champion: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    icp_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)  # draft | escalate
    product_fit: Mapped[str | None] = mapped_column(String(32), nullable=True)  # Pro | Hive | Both

    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    bulk_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    force_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    research_cycles: Mapped[int] = mapped_column(Integer, default=1)

    drafts: Mapped[list["Draft"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    safety_checks: Mapped[list["SafetyCheck"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    citations: Mapped[list["Citation"]] = relationship(back_populates="run", cascade="all, delete-orphan")

    composio_draft_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    composio_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drafted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Persisted SSE event log — captures every agent.status / agent.tool /
    # agent.result line for replay when the run is revisited later.
    events_history: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("runs.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    subject: Mapped[str] = mapped_column(Text)
    greeting: Mapped[str] = mapped_column(Text, default="")
    introduction: Mapped[str] = mapped_column(Text, default="")
    pain_point: Mapped[str] = mapped_column(Text, default="")
    product_desc: Mapped[str] = mapped_column(Text, default="")
    bullet_points: Mapped[list] = mapped_column(JSON, default=list)
    cta: Mapped[str] = mapped_column(Text, default="")
    html: Mapped[str] = mapped_column(Text, default="")
    approved_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["Run"] = relationship(back_populates="drafts")


class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("runs.id", ondelete="CASCADE"))
    agent: Mapped[str] = mapped_column(String(32))  # lead_enrichment | market_intelligence | ...
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="citations")


class SafetyCheck(Base):
    __tablename__ = "safety_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("runs.id", ondelete="CASCADE"))
    check_name: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(Boolean)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["Run"] = relationship(back_populates="safety_checks")


class Bulk(Base):
    __tablename__ = "bulks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total: Mapped[int] = mapped_column(Integer, default=0)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
