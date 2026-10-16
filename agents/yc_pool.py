"""Discovery's wider source: every company in recent Y Combinator batches.

Data comes from the open yc-oss dataset (https://yc-oss.github.io/api), which
mirrors YC's public company pages: website, team size, industry, description.
Nothing is scraped from ycombinator.com's directory (its robots.txt disallows
that).

The point of this module is to spend as little as possible finding a company
whose decision-maker email can actually be found. Two things do that:

1. A free local pre-screen with the same ICP guardrail the pipeline uses, so
   hardware companies, infrastructure tooling, services firms and companies
   too large for the ICP never reach a paid lookup.
2. Ranking by what past lookups taught us. The contact finder records every
   result in `lookup_history`; here the hit rate seen so far for the same
   batch, team-size band and market decides who is tried first. Before there
   is any history, larger and hiring companies go first - they are more likely
   to be in a contact database than a three-person company from this month.
"""
import re
from collections import defaultdict
from typing import Optional

import requests

import config
import storage
from agents import classify, icp
from models import Lead

API = "https://yc-oss.github.io/api/batches/{slug}.json"
HEADERS = {"User-Agent": "SerfisLeadGenBot/0.1 (capstone project)"}


def _batch_label(slug: str) -> str:
    season, year = slug.split("-")
    return f"{season.capitalize()} {year}"


def _load_batch(slug: str) -> list[dict]:
    try:
        resp = requests.get(API.format(slug=slug), headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return []


def _text(c: dict) -> str:
    return " ".join([c.get("one_liner") or "", c.get("long_description") or "",
                     " ".join(c.get("tags") or []), c.get("subindustry") or ""])


def _as_lead(c: dict) -> Lead:
    team = int(c.get("team_size") or 0)
    return Lead(
        company_name=c["name"], website=c.get("website") or "", source="yc_directory",
        category=c.get("subindustry") or c.get("industry") or "",
        industry=c.get("industry") or "", what_they_sell=c.get("one_liner") or "",
        company_size=classify.band_for(team) if team else "", yc_batch=c.get("batch") or "",
        yc_profile_url=c.get("url") or "",
    )


def passes_prescreen(c: dict) -> Optional[Lead]:
    """The ICP guardrail applied to dataset facts alone (free). Returns the
    classified Lead if it passes, else None."""
    if c.get("status") != "Active" or not c.get("website") or c.get("nonprofit"):
        return None
    lead = _as_lead(c)
    text = _text(c)
    icp.classify(lead, text)
    return lead if not icp.rejection_reasons(lead, text) else None


def learned_scores() -> dict:
    """Smoothed hit rate per (dimension, value) from lookup_history."""
    counts = defaultdict(lambda: [0, 0])          # key -> [hits, tries]
    for row in storage.lookup_stats():
        for dim in ("batch", "size_band", "market"):
            if row[dim]:
                k = (dim, row[dim])
                counts[k][1] += 1
                counts[k][0] += 1 if row["outcome"] == "hit" else 0
    return {k: (h + 0.5) / (n + 5) for k, (h, n) in counts.items()}   # prior ~10%


def _rank(c: dict, lead: Lead, scores: dict) -> float:
    prior = 0.10
    s = 1.0
    for dim, val in (("batch", lead.yc_batch), ("size_band", lead.company_size), ("market", lead.market)):
        s *= scores.get((dim, val), prior) / prior
    team = int(c.get("team_size") or 0)
    s *= 1 + min(team, 50) / 25                    # bigger teams are likelier to be in a contact database
    s *= 1.3 if c.get("isHiring") else 1.0
    s *= 1 + 0.15 * max(icp.fit_rank(lead.serfis_fit), 0)   # tie-break toward the better ICP fit
    return s


def candidates(skip_domains: set, skip_names: set, limit: int) -> tuple[list[tuple[dict, Lead]], dict]:
    """Best-ranked companies that pass the pre-screen and haven't been tried.
    Also returns a small report: how many were scanned / screened out."""
    scores = learned_scores()
    scanned = screened_out = 0
    pool = []
    for slug in config.YC_BATCHES:
        for c in _load_batch(slug):
            scanned += 1
            if storage.domain_of(c.get("website")) in skip_domains or re.sub(r"[^a-z0-9]", "", c["name"].lower()) in skip_names:
                continue
            lead = passes_prescreen(c)
            if lead is None:
                screened_out += 1
                continue
            pool.append((_rank(c, lead, scores), c, lead))
    pool.sort(key=lambda t: -t[0])
    report = {"scanned": scanned, "screened_out": screened_out, "eligible": len(pool),
              "learned": {f"{d}={v}": round(r, 2) for (d, v), r in scores.items()}}
    return [(c, lead) for _, c, lead in pool[:limit]], report


def with_published_email(picked: list, want: int, workers: int = 8) -> tuple:
    """Free filter: of the ranked candidates, keep those whose own site publishes an
    email for one of their YC founders. Returns ([(company, lead, contact)], checked).
    Stops once `want` are found."""
    from concurrent.futures import ThreadPoolExecutor
    from agents import site_emails, yc

    def check(item):
        c, lead = item
        emails = site_emails.personal(site_emails.own_domain_emails(lead.website))
        if not emails:
            return None
        profile = yc.fetch_profile(lead.yc_profile_url)
        if not profile or not profile["founders"]:
            return None
        lead.founders = "\n".join(
            f"{f['name']} ({f['title']})" if f["title"] else f["name"] for f in profile["founders"])
        contact = site_emails.match_founder(emails, lead.founders)
        if contact:
            for f in profile["founders"]:
                if f["name"] == contact["name"]:
                    contact["linkedin"] = f.get("linkedin") or ""
        return (c, lead, contact) if contact else None

    found, checked, missed = [], 0, []
    for i in range(0, len(picked), workers * 4):
        chunk = picked[i:i + workers * 4]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(check, chunk))
        checked += len(chunk)
        found += [r for r in results if r]
        missed += [item for item, r in zip(chunk, results) if not r]
        if len(found) >= want:
            break
    return found[:want], checked, missed


def with_linkedin_email(missed: list, want: int, max_profiles: int, workers: int = 4) -> tuple:
    """Second pass for companies whose site published nothing: read the founders' LinkedIn profiles
    and keep an email only if the founder wrote it on the profile (never a guess). Paid (~$0.004 per
    profile), so it stops at `max_profiles` reads. Returns ([(company, lead, contact)], profiles_read)."""
    from concurrent.futures import ThreadPoolExecutor
    from agents import linkedin
    start = linkedin.paid_reads

    def check(item):
        c, lead = item
        hit = linkedin.find_explicit_email(lead)
        if not hit:
            return None
        hit["source"] = "linkedin"
        return (c, lead, hit)

    found = []
    for i in range(0, len(missed), workers):
        if len(found) >= want or linkedin.paid_reads - start >= max_profiles:
            break
        with ThreadPoolExecutor(max_workers=workers) as pool:
            found += [r for r in pool.map(check, missed[i:i + workers]) if r]
    return found[:want], linkedin.paid_reads - start
