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
