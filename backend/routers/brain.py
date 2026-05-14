from fastapi import APIRouter
from pydantic import BaseModel
from services import brain as brain_svc

router = APIRouter(prefix="/api/brain", tags=["brain"])


@router.get("")
def get_brain():
    return brain_svc.load_brain()


@router.put("")
def put_brain(payload: dict):
    brain_svc.save_brain(payload)
    return {"ok": True, "brain": brain_svc.load_brain()}
