"""Step 1: find companies that fit the ICP (SaaS, SMB, recently VC-funded startups).

MVP behavior:
- DEMO_MODE (no Apify token): reads data/seed_companies.csv.
- Real mode (APIFY_API_TOKEN set): runs an Apify Actor
  (config.APIFY_DISCOVERY_ACTOR, default compass/crawler-google-places -
  the "Google Maps Scraper") to find real businesses by search term.

History: the original discovery Actor choice was a low-usage Crunchbase
search scraper (automation-lab/crunchbase-company-funding-search-scraper).
Live testing showed it is not currently functional - Crunchbase's anti-bot
protection rejects its scraping sessions outright (confirmed via the Actor's
own run logs: "session challenge not cleared (HTTP 403)", failing across
all 6 retry attempts). Switched to Google Maps Scraper instead - still an
Apify Actor, but one of the most established on the entire platform
(612K+ users, 4.7 stars, 1,800+ reviews) rather than an unproven one.

Tradeoff: Google Maps search is location-bound rather than funding-filtered,
so it can't replicate Apollo's "recently funded" filter directly - results
are seeded from ICP_SEARCH_QUERIES + a location, and funding status still
gets left for ResearchAgent to try to confirm from the company's own site.
"""
import csv
import re
import time
from dataclasses import dataclass
from typing import Optional

import config
import storage
from agents import icp, yc, yc_pool
from agents.apify_client import run_actor


@dataclass
class DiscoveredCompany:
    company_name: str
    website: str
    source: str
    funding_hint: str = ""
    # Filled for companies on the prospect tracker (data/target_companies.csv)
    priority: str = ""
    category: str = ""
    market: str = ""
    what_they_do: str = ""
    why_serfis_fit: str = ""
    content_angle: str = ""
    best_ad_type: str = ""
    serfis_fit: str = ""
    yc_profile_url: str = ""
    # Set when discovery already found a published founder email (free route)
    contact_name: str = ""
    contact_title: str = ""
    contact_email: str = ""
    contact_linkedin: str = ""
    contact_source: str = ""        # "published" (company site) or "linkedin" (founder's profile)
    founders: str = ""


# Search terms sent to the discovery Actor - stand in for Apollo's
# structured industry filters, since Google Maps Scraper takes free-text
# search terms + a location rather than structured filters.
ICP_SEARCH_QUERIES = ["AI app startup", "consumer AI startup", "AI agent startup"]
ICP_LOCATION = "United States"


class DiscoveryAgent:
    def discover(self, limit: int = 10) -> list[DiscoveredCompany]:
        self.notes: list[str] = []
        if config.DEMO_MODE or not config.APIFY_API_TOKEN:
            return self._discover_from_seed(limit)
        # The prospect tracker comes first: those are the companies Serfis
        # already wants. Open-ended search only runs once the tracker has
        # nothing left (everything on it is already a lead), because search
        # results mostly fail the ICP guardrail and cost Apify credits.
        found = self._discover_from_watchlist(limit)
        if found:
            return found
        self.notes.append("Prospect tracker exhausted - drawing from recent YC batches.")
        return self._discover_from_yc_pool(limit)

    def _discover_from_yc_pool(self, limit: int) -> list[DiscoveredCompany]:
        """Companies from recent YC batches that pass the ICP pre-screen, best-ranked first
        (ranking learns from past lookup results). Skips leads and anything already looked up."""
        norm = lambda t: re.sub(r"[^a-z0-9]", "", (t or "").lower())
        domains = storage.looked_up_domains()
        names = set()
        for lead in storage.get_all_leads():
            domains.add(storage.domain_of(lead.website))
            names.add(norm(lead.company_name))
        picked, report = yc_pool.candidates(domains, names, limit=1000)
        self.notes.append(
            f"YC pool: scanned {report['scanned']}, screened out {report['screened_out']} "
            f"(not ICP), {report['eligible']} eligible."
        )
        # Free check on every eligible company: keep only those whose own site publishes a
        # founder's email. No paid lookup is spent on anyone else.
        picked, checked, missed = yc_pool.with_published_email(picked, want=limit)
        self.notes.append(f"Checked {checked} company sites for a published founder email; "
                          f"{len(picked)} publish one.")
        if len(picked) < limit and config.LINKEDIN_EMAILS and config.APIFY_API_TOKEN and missed:
            li, reads = yc_pool.with_linkedin_email(missed, limit - len(picked), config.LINKEDIN_SCAN_MAX_PROFILES)
            self.notes.append(f"Read {reads} founder LinkedIn profiles for an email they wrote themselves; {len(li)} had one.")
            picked += li
        if report["learned"]:
            self.notes.append(f"Learned lookup hit rates: {report['learned']}")
        out = []
        for c, lead, contact in picked:
            out.append(DiscoveredCompany(
                contact_name=contact["name"], contact_title=contact["title"],
                contact_email=contact["email"], contact_linkedin=contact.get("linkedin", ""),
                contact_source=contact.get("source", "published"),
                founders=lead.founders,
                company_name=lead.company_name, website=lead.website, source="yc_directory",
                funding_hint=f"Y Combinator {lead.yc_batch}".strip(),
                priority=lead.priority, category=lead.category, market=lead.market,
                what_they_do=lead.what_they_sell, why_serfis_fit=lead.why_it_fits,
                content_angle=lead.content_angle, best_ad_type=lead.best_ad_type,
                serfis_fit=lead.serfis_fit, yc_profile_url=lead.yc_profile_url,
            ))
        return out

    def _discover_from_watchlist(self, limit: int) -> list[DiscoveredCompany]:
        """P1 then P2 companies from data/target_companies.csv that aren't leads yet.
        P3 (research-only comparables) and unreviewed rows are never returned."""
        if not config.WATCHLIST_CSV.exists():
            return []
        norm = lambda t: re.sub(r"[^a-z0-9]", "", (t or "").lower())
        known = set()
        for lead in storage.get_all_leads():
            known.add(norm(lead.company_name))
            known.add(norm(lead.website))
        looked_up = storage.looked_up_domains()
        with open(config.WATCHLIST_CSV, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["priority"] in icp.PRIORITY_OK]
        rows.sort(key=lambda r: r["priority"])          # stable: P1 first, tracker order kept
        out = []
        for row in rows:
            if len(out) >= limit:
                break
            if norm(row["company"]) in known:
                continue
            profile = yc.fetch_profile(row["yc_profile_url"])
            time.sleep(0.5)                              # polite to ycombinator.com
            if not profile or not profile["website"]:
                self.notes.append(f"{row['company']}: could not read its YC profile - skipped.")
                continue
            if norm(profile["website"]) in known or storage.domain_of(profile["website"]) in looked_up:
                continue
            out.append(DiscoveredCompany(
                company_name=row["company"], website=profile["website"], source="prospect_tracker",
                funding_hint=f"Y Combinator {profile['batch']}".strip(),
                priority=row["priority"], category=row["category"], market=row["market"],
                what_they_do=row["what_they_do"], why_serfis_fit=row["why_serfis_fit"],
                content_angle=row["content_angle"], best_ad_type=row["best_ad_type"],
                serfis_fit=row["serfis_fit"], yc_profile_url=row["yc_profile_url"],
            ))
        return out

    def _discover_from_seed(self, limit: int) -> list[DiscoveredCompany]:
        if not config.SEED_COMPANIES_CSV.exists():
            return []
        out = []
        with open(config.SEED_COMPANIES_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out.append(
                    DiscoveredCompany(
                        company_name=row["company_name"].strip(),
                        website=row["website"].strip(),
                        source="seed_csv",
                        funding_hint=row.get("funding_hint", "").strip(),
                    )
                )
                if len(out) >= limit:
                    break
        return out

    def _discover_from_apify(self, limit: int) -> list[DiscoveredCompany]:
        run_input = {
            "searchStringsArray": ICP_SEARCH_QUERIES,
            "locationQuery": ICP_LOCATION,
            "maxCrawledPlacesPerSearch": limit,
        }
        items = run_actor(config.APIFY_DISCOVERY_ACTOR, run_input, timeout=180)
        out = []
        for item in items:
            company = self._parse_result(item)
            if company:
                out.append(company)
            if len(out) >= limit:
                break
        return out

    def _parse_result(self, item: dict) -> Optional[DiscoveredCompany]:
        """Defensive parsing - checks a few likely field-name variants."""
        name = item.get("title") or item.get("name")
        website = item.get("website") or item.get("url")
        if not name or not website:
            return None

        category = item.get("categoryName") or item.get("category") or ""
        funding_hint = f"Google Maps category: {category}" if category else ""

        return DiscoveredCompany(
            company_name=name,
            website=website,
            source="apify_google_maps",
            funding_hint=funding_hint,
        )
