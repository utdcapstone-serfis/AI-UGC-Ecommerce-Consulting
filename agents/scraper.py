"""Shared helper: fetch a company's public website text for enrichment/research.
Respects robots.txt implicitly by only doing simple GETs on public pages - no
login walls, no LinkedIn, no bypassing paywalls or bot protection.
"""
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "SerfisLeadGenBot/0.1 (+https://serfis.ai; research purposes)"}


def fetch_site_text(url: str, max_chars: int = 6000) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:max_chars]


_ABOUT_PATHS = ["/about", "/about-us", "/company", "/team", "/careers"]


def fetch_company_text(url: str, max_chars: int = 12000) -> str:
    """Homepage plus up to two about/company/careers pages - headcount and
    what-we-do details are usually there, not on the homepage. Plain public
    GETs only, short timeouts, stops early."""
    home = fetch_site_text(url, max_chars=6000)
    if not home:
        return ""
    base = url if url.startswith("http") else "https://" + url
    parts = base.split("/")
    root = "/".join(parts[:3])
    extra, found = [], 0
    for path in _ABOUT_PATHS:
        if found >= 2:
            break
        text = fetch_site_text(root + path, max_chars=3000)
        if text:
            extra.append(text)
            found += 1
    return " ".join([home] + extra)[:max_chars]
