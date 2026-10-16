"""Reads a public Y Combinator company profile (ycombinator.com/companies/<slug>).

Gives the discovery and enrichment agents the facts the tracker doesn't have:
the company's real website, team size, location, batch, one-liner, tags and
founders. One polite GET per company (robots.txt allows /companies/<slug>), no
login, results cached for the life of the process.
"""
import html
import json
import re
from functools import lru_cache
from typing import Optional

import requests

HEADERS = {"User-Agent": "SerfisLeadGenBot/0.1 (+https://serfis.ai; research purposes)"}


@lru_cache(maxsize=128)
def fetch_profile(url: str) -> Optional[dict]:
    """Returns the profile as a plain dict, or None if it can't be read."""
    if not url or "ycombinator.com/companies/" not in url:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    m = re.search(r'data-page="([^"]+)"', resp.text)
    if not m:
        return None
    try:
        company = json.loads(html.unescape(m.group(1))).get("props", {}).get("company") or {}
    except ValueError:
        return None
    if not company.get("name"):
        return None

    founders = []
    for f in company.get("founders") or []:
        name = f.get("full_name") or " ".join(filter(None, [f.get("first_name"), f.get("last_name")]))
        if name:
            founders.append({
                "name": name.strip(),
                "title": (f.get("title") or "").strip(),
                "bio": (f.get("founder_bio") or "").strip(),
                "linkedin": f.get("linkedin_url") or "",
            })
    return {
        "name": company.get("name", ""),
        "website": (company.get("website") or "").strip(),
        "one_liner": (company.get("one_liner") or "").strip(),
        "long_description": (company.get("long_description") or "").strip(),
        "team_size": company.get("team_size"),
        "location": (company.get("location") or "").strip(),
        "batch": (company.get("batch_name") or "").strip(),
        "year_founded": company.get("year_founded"),
        "tags": company.get("tags") or [],
        "founders": founders,
    }
