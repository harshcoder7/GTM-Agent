"""Light-touch site scraper for ICP product summary.

Fetches a domain's homepage + a couple of common product/solutions paths and
concatenates the visible text (capped) for the product-summary LLM call.
"""
from __future__ import annotations
import asyncio
import httpx
from bs4 import BeautifulSoup

CANDIDATE_PATHS = ["/", "/products", "/product", "/solutions", "/platform", "/services", "/about"]


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip()
    if not d:
        return ""
    if not d.startswith(("http://", "https://")):
        d = "https://" + d
    return d.rstrip("/")


async def _fetch(url: str, cx: httpx.AsyncClient) -> str:
    try:
        r = await cx.get(url, follow_redirects=True, timeout=15)
        if r.status_code != 200 or not r.text:
            return ""
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:6000]
    except Exception:
        return ""


async def scrape_site(domain: str, *, max_chars: int = 18000) -> str:
    base = _normalize_domain(domain)
    if not base:
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GTM-Agent/0.1)"}
    async with httpx.AsyncClient(headers=headers) as cx:
        tasks = [_fetch(base + p, cx) for p in CANDIDATE_PATHS]
        chunks = await asyncio.gather(*tasks, return_exceptions=False)
    joined = "\n\n".join([c for c in chunks if c])
    return joined[:max_chars]
