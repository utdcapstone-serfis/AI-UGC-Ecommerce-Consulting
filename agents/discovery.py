"""Step 1: find companies that fit the ICP (SaaS, SMB, recently VC-funded startups).

MVP behavior:
- DEMO_MODE (no Apify token): reads data/seed_companies.csv.
- Real mode (APIFY_API_TOKEN set): runs an Apify Actor
  (config.APIFY_DISCOVERY_ACTOR, default automation-lab/crunchbase-company-
  funding-search-scraper) that searches Crunchbase by keyword and can filter
  to companies with reported funding rounds.

Note: unlike the contact-finding Actor (60K+ users, well-established), the
discovery Actor is low-usage/unproven at the time this was wired up. The
input schema (queries/maxItems/requireFunding) was confirmed directly from
the Actor's published schema; the exact output field names were not fully
confirmed before a live token was available - _parse_result() below checks
several likely field name variants defensively and should be revisited
against real output once you've run this for real.
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


# Keyword queries sent to the discovery Actor - stand in for Apollo's
# structured industry/employee-count filters, since this Actor only takes
# free-text search queries.
ICP_SEARCH_QUERIES = ["SaaS startup", "software company"]


class DiscoveryAgent:
    def discover(self, limit: int = 10) -> list[DiscoveredCompany]:
        # DEMO_MODE only requires ONE of Apify/Hunter to be set (see config.py).
        # Discovery specifically needs Apify - if only a Hunter key was added,
        # still fall back to the seed list here rather than calling Apify
        # with a blank token.
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
            "queries": ICP_SEARCH_QUERIES,
            "maxItems": limit,
            "requireFunding": True,
        }
        items = run_actor(config.APIFY_DISCOVERY_ACTOR, run_input)
        out = []
        for item in items[:limit]:
            company = self._parse_result(item)
            if company:
                out.append(company)
        return out

    def _parse_result(self, item: dict) -> Optional[DiscoveredCompany]:
        """Defensive parsing - checks a few likely field-name variants since
        the exact output schema wasn't confirmed before this was written."""
        name = item.get("name") or item.get("companyName") or item.get("title")
        website = (
            item.get("website")
            or item.get("homepageUrl")
            or item.get("website_url")
            or item.get("url")
        )
        if not name or not website:
            return None

        funding_type = item.get("lastFundingType") or item.get("last_funding_type") or ""
        funding_hint = f"Crunchbase: {funding_type}" if funding_type else ""

        return DiscoveredCompany(
            company_name=name,
            website=website,
            source="apify_crunchbase",
            funding_hint=funding_hint,
        )
