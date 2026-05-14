from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Ensure parent dir exists for sqlite file
_url = settings.database_url
if _url.startswith("sqlite:///"):
    path = _url.replace("sqlite:///", "", 1)
    if path and path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _lightweight_migrate()


def _lightweight_migrate() -> None:
    """Add columns SQLAlchemy doesn't auto-add via create_all."""
    if "sqlite" not in str(engine.url):
        return
    add_cols = [
        ("runs", "events_history", "JSON"),
        ("runs", "research_cycles", "INTEGER DEFAULT 1"),
    ]
    with engine.begin() as cx:
        for table, col, ctype in add_cols:
            try:
                existing = [r[1] for r in cx.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]
                if col not in existing:
                    cx.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}")
            except Exception:
                pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
