"""Ports the Langflow EmailTextFormatter + BulletPointsHTMLGenerator + Brochure
Switcher + final body template into one server-side render function.

Input: an EmailDraft (subject + greeting + introduction + pain_point +
product_desc + bullet_points[] + cta), plus product_fit (Pro | Hive | Both).

Output: a single HTML string ready to drop into a Gmail body (is_html=true).
"""
from __future__ import annotations
import re

PINK = "rgb(204,43,156)"
BLUE = "rgb(140,172,228)"

# Single-brochure default. Override via the company brain's product.brochure_url.
DEFAULT_BROCHURE_URL = "https://www.zamp.ai"
DEFAULT_BROCHURE_LABEL = "Pace"
FOOTER_LINK_URL = "https://www.zamp.ai"
FOOTER_LINK_LABEL = "Zamp AI"


def _apply_inline_markdown(text: str) -> str:
    if not text:
        return ""
    # ***triple*** → bold pink
    text = re.sub(r"\*\*\*(.*?)\*\*\*", rf'<span style="color:{PINK};font-weight:600;">\1</span>', text)
    # **double** → medium pink
    text = re.sub(r"\*\*(.*?)\*\*", rf'<span style="color:{PINK};font-weight:500;">\1</span>', text)
    # *single* → italic
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
    # `code`
    text = re.sub(r"`(.*?)`", r'<code style="background:#f1f3f4;padding:2px 4px;border-radius:3px;font-family:monospace;font-size:14px;">\1</code>', text)
    return text


def _bullet_list_html(items: list[str]) -> str:
    if not items:
        return ""
    lis = []
    for txt in items:
        formatted = _apply_inline_markdown(txt)
        lis.append(
            f'<li style="display:flex;align-items:flex-start;margin:16px 0;">'
            f'<div style="width:6px;height:6px;background:{BLUE};border-radius:50%;margin-top:10px;margin-right:12px;flex-shrink:0;"></div>'
            f'<div style="flex:1;font-size:15px;line-height:1.6;color:#333;">{formatted}</div>'
            f"</li>"
        )
    return '<ul style="margin:0;padding:0;list-style:none;">' + "".join(lis) + "</ul>"


def brochure_html(_product_fit: str | None = None) -> str:
    """Single brochure / deck block. Pulls URL + product label from the company brain
    (first configured product); falls back to the Zamp defaults above."""
    try:
        from services import brain  # local import to avoid circular at module load
        b = brain.load_brain()
        product = (b.get("products") or [{}])[0] or {}
        label = product.get("name") or DEFAULT_BROCHURE_LABEL
        url = product.get("brochure_url") or DEFAULT_BROCHURE_URL
    except Exception:
        label = DEFAULT_BROCHURE_LABEL
        url = DEFAULT_BROCHURE_URL

    # Use a slide/deck icon — clearer "this is a deck" affordance than the doc icon.
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
            'fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'style="width:16px;height:16px;vertical-align:middle;margin-right:6px;">'
            '<rect x="2" y="3" width="20" height="14" rx="2"/>'
            '<line x1="8" y1="21" x2="16" y2="21"/>'
            '<line x1="12" y1="17" x2="12" y2="21"/></svg>')
    link = (
        f'<a href="{url}" style="color:{PINK};text-decoration:none;font-weight:500;'
        f'display:inline-flex;align-items:center;gap:6px;">{icon}Open the {label} deck</a>'
    )
    return (
        f'<div style="margin:32px 0;padding:20px;background:linear-gradient(135deg,#f8f9ff,#fff5f8);'
        f'border-radius:8px;border-left:4px solid {PINK};">'
        f'<div style="font-size:15px;font-weight:600;color:#1a1a1a;margin-bottom:8px;">A quick look at {label}</div>'
        f"{link}</div>"
    )


def render_email_html(draft: dict, product_fit: str | None = None) -> str:
    greeting = _apply_inline_markdown(draft.get("greeting", ""))
    intro = _apply_inline_markdown(draft.get("introduction", ""))
    pain = _apply_inline_markdown(draft.get("pain_point", ""))
    product = _apply_inline_markdown(draft.get("product_desc", ""))
    bullets = _bullet_list_html(draft.get("bullet_points", []))
    cta = draft.get("cta", "")
    brochure = brochure_html(product_fit)
    return f"""<body style="font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif;line-height:1.6;color:#1a1a1a;background:#f8f9fa;padding:20px 0;margin:0;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e9ecef;border-radius:8px;overflow:hidden;">
    <div style="padding:40px;">
      <div style="font-size:16px;color:#1a1a1a;margin-bottom:24px;font-weight:500;">{greeting}</div>
      <div style="margin-bottom:24px;font-size:15px;line-height:1.7;color:#333;">{intro}</div>
      <div style="margin-bottom:24px;font-size:15px;line-height:1.7;color:#333;">{pain}</div>
      <div style="margin:32px 0;">
        <div style="font-size:15px;line-height:1.7;color:#333;margin-bottom:20px;">{product}</div>
        {bullets}
      </div>
      {brochure}
      <div style="margin-top:40px;padding-top:32px;border-top:1px solid #f1f3f4;">
        <div style="font-size:16px;font-weight:600;color:{PINK};">{cta}</div>
      </div>
    </div>
    <div style="background:#f8f9fa;padding:20px 40px;text-align:center;font-size:12px;color:#666;border-top:1px solid #f1f3f4;">
      <a href="{FOOTER_LINK_URL}" style="color:{BLUE};text-decoration:none;font-weight:500;">{FOOTER_LINK_LABEL}</a>
    </div>
  </div>
</body>"""
