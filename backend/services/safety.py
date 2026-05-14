"""Safety checks that run at Gate 1 before the rep can approve.

Returns a list of {check, passed, explanation} dicts.
"""
from __future__ import annotations
import re
from services import brain
from config import settings

_PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}|\[[A-Z_]{3,}\]")
_SPAMMY_WORDS = ["free!!!", "act now", "limited time", "guaranteed", "click here", "$$$"]


def check_placeholder_leak(draft: dict) -> dict:
    text = " ".join([
        draft.get("subject", ""),
        draft.get("greeting", ""),
        draft.get("introduction", ""),
        draft.get("pain_point", ""),
        draft.get("product_desc", ""),
        " ".join(draft.get("bullet_points", []) or []),
        draft.get("cta", ""),
    ])
    m = _PLACEHOLDER_RE.search(text)
    if m:
        return {"check": "placeholder_leak", "passed": False,
                "explanation": f"Unfilled placeholder detected: '{m.group(0)}'."}
    return {"check": "placeholder_leak", "passed": True, "explanation": "No unfilled placeholders."}


def check_spammy_subject(draft: dict) -> dict:
    s = (draft.get("subject", "") or "").lower()
    hits = [w for w in _SPAMMY_WORDS if w in s]
    if hits:
        return {"check": "spammy_subject", "passed": False,
                "explanation": f"Subject contains spam-trigger phrase(s): {', '.join(hits)}."}
    if len(draft.get("subject", "")) > 90:
        return {"check": "spammy_subject", "passed": False,
                "explanation": "Subject is too long (>90 chars) — looks like a paragraph."}
    return {"check": "spammy_subject", "passed": True, "explanation": "Subject reads clean."}


def check_icp_fit(icp: dict | None) -> dict:
    if not icp:
        return {"check": "icp_fit", "passed": False, "explanation": "ICP not yet scored."}
    score = icp.get("icp_score")
    try:
        s = float(score) if score is not None else 0
    except (TypeError, ValueError):
        s = 0
    if s < 5:
        return {"check": "icp_fit", "passed": False,
                "explanation": f"ICP score {s} is below 5 — outreach not recommended."}
    return {"check": "icp_fit", "passed": True, "explanation": f"ICP score {s} ≥ 5."}


def check_brochure_attached(product_fit: str | None) -> dict:
    if not product_fit:
        return {"check": "brochure_attached", "passed": False,
                "explanation": "No product_fit set — brochure block missing."}
    if product_fit not in ("Pro", "Hive", "Both"):
        return {"check": "brochure_attached", "passed": False,
                "explanation": f"Invalid product_fit '{product_fit}' — expected Pro / Hive / Both."}
    return {"check": "brochure_attached", "passed": True,
            "explanation": f"Brochure block will render for '{product_fit}'."}


def check_recipient_allowlist(recipient: str | None) -> dict:
    # In draft mode the email only lands in the user's own inbox — no real
    # send happens — so the allowlist is informational, not blocking.
    is_draft_mode = (settings.send_mode or "draft").lower() in ("draft", "mock")

    if not recipient:
        passed = is_draft_mode
        return {"check": "recipient_allowlist", "passed": passed,
                "explanation": "No recipient email on the prospect."
                               + ("" if passed else " (required for real send)")}
    allow = brain.allowlist()
    if not allow:
        return {"check": "recipient_allowlist", "passed": True,
                "explanation": "No allowlist configured."}
    if recipient.strip().lower() in allow:
        return {"check": "recipient_allowlist", "passed": True,
                "explanation": f"{recipient} is on the allowlist."}
    # Not on the allowlist — block real-send, allow draft.
    if is_draft_mode:
        return {"check": "recipient_allowlist", "passed": True,
                "explanation": f"Draft mode — {recipient} not on allowlist (only matters when SEND_MODE=send)."}
    return {"check": "recipient_allowlist", "passed": False,
            "explanation": f"{recipient} is NOT on the allowlist (required for SEND_MODE=send)."}


def run_all(draft: dict, icp: dict | None, product_fit: str | None, recipient: str | None) -> list[dict]:
    return [
        check_placeholder_leak(draft),
        check_spammy_subject(draft),
        check_icp_fit(icp),
        check_brochure_attached(product_fit),
        check_recipient_allowlist(recipient),
    ]
