from __future__ import annotations
import csv
import io
import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db import models
from graph import fire_and_forget

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


@router.post("")
async def bulk_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    text = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    bulk_id = uuid.uuid4().hex[:12]
    db.add(models.Bulk(id=bulk_id, total=0, filename=file.filename or "upload.csv"))
    db.commit()

    run_ids = []
    count = 0
    for row in reader:
        prospect = {
            "full_name": row.get("Name") or row.get("full_name") or "",
            "company": row.get("Company") or row.get("Company Name") or row.get("company") or "",
            "linkedin_url": row.get("Linkedin") or row.get("LinkedIn") or row.get("linkedin_url") or "",
            "job_title": row.get("Title") or row.get("job_title") or "",
            "email": row.get("Email") or row.get("email") or "",
            "domain": row.get("Domain") or row.get("Company Domain") or row.get("domain") or "",
        }
        if not prospect["full_name"] and not prospect["company"]:
            continue
        rid = uuid.uuid4().hex[:12]
        db.add(models.Run(id=rid, prospect_json=prospect, bulk_id=bulk_id, status="queued"))
        run_ids.append(rid)
        count += 1
    db.query(models.Bulk).filter_by(id=bulk_id).update({"total": count})
    db.commit()
    for rid in run_ids:
        fire_and_forget(rid)
    return {"bulk_id": bulk_id, "count": count, "run_ids": run_ids}
