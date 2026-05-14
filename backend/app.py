from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from config import settings
from db.session import init_db
from routers import runs, brain, bulk, dashboard, composio, keys

app = FastAPI(title="GTM Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # cache preflight responses for 24h
)


@app.on_event("startup")
def _startup():
    init_db()
    # Any runs that were in-flight when the backend was killed are stranded —
    # their asyncio tasks are gone. Mark them cancelled so the dashboard is honest.
    from db.session import SessionLocal
    from db import models
    db = SessionLocal()
    try:
        IN_FLIGHT = ("queued", "enriching", "market", "icp", "person", "champion", "drafting")
        stale = db.query(models.Run).filter(models.Run.status.in_(IN_FLIGHT)).all()
        for r in stale:
            r.status = "cancelled"
            r.escalation_reason = (r.escalation_reason or "") + " | cancelled on backend restart"
        if stale:
            db.commit()
            print(f"[startup] cancelled {len(stale)} stale run(s)", flush=True)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "send_mode": settings.send_mode}


app.include_router(runs.router)
app.include_router(brain.router)
app.include_router(bulk.router)
app.include_router(dashboard.router)
app.include_router(composio.router)
app.include_router(keys.router)
