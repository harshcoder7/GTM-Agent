from __future__ import annotations
import os
import shutil
import yaml
from pathlib import Path
from config import settings

# Writes go to the persisted data volume. First read seeds from the image-baked
# defaults if no persisted file exists yet.
_DATA_PATH = Path(settings.brain_path)
_SEED_PATH = Path(settings.brain_seed_path)
_FALLBACK_PATH = Path(__file__).resolve().parent.parent / "company_brain.yaml"


def _ensure_seeded() -> Path:
    """Make sure a persisted brain file exists; seed from image defaults if not."""
    if _DATA_PATH.exists():
        return _DATA_PATH
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    for src in (_SEED_PATH, _FALLBACK_PATH):
        if src.exists():
            try:
                shutil.copy(src, _DATA_PATH)
                return _DATA_PATH
            except Exception:
                pass
    # No seed available — return the writable path even if empty
    return _DATA_PATH


def load_brain() -> dict:
    p = _ensure_seeded()
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def save_brain(data: dict) -> None:
    p = _DATA_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def product_context_block() -> str:
    """Render the products list into a multi-paragraph string for prompts."""
    brain = load_brain()
    out: list[str] = []
    for p in brain.get("products", []):
        out.append(f"- **{p['name']}**: {p['short']}")
        sigs = p.get("fit_signals", [])
        if sigs:
            out.append("  Fit signals: " + ", ".join(sigs))
    return "\n".join(out) if out else "(no products configured)"


def target_icp() -> str:
    return load_brain().get("target_icp", "")


def sender_block() -> dict:
    return load_brain().get("company", {})


def brochure_url(product_name: str) -> str | None:
    for p in load_brain().get("products", []):
        if p.get("name", "").lower() == product_name.lower():
            return p.get("brochure_url")
    return None


def allowlist() -> list[str]:
    return [e.strip().lower() for e in load_brain().get("allowlist_emails", []) if e]
