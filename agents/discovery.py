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
from dataclasses import dataclass
from typing import Optional

import config
from agents.apify_client import run_actor


@dataclass
class DiscoveredCompany:
    company_name: str
    website: str
    source: str
    funding_hint: str = ""


# Search terms sent to the discovery Actor - stand in for Apollo's
# structured industry filters, since Google Maps Scraper takes free-text
# search terms + a location rather than structured filters.
ICP_SEARCH_QUERIES = ["software company", "SaaS startup", "tech startup"]
ICP_LOCATION = "United States"


class DiscoveryAgent:
    def discover(self, limit: int = 10) -> list[DiscoveredCompany]:
        if config.DEMO_MODE or not config.APIFY_API_TOKEN:
            return self._discover_from_seed(limit)
        return self._discover_from_apify(limit)

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
