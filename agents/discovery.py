"""Step 1: find companies that fit the ICP (SaaS, SMB, recently VC-funded startups).

MVP behavior:
- DEMO_MODE (no Apollo key): reads data/seed_companies.csv.
- Real mode (APOLLO_API_KEY set): queries Apollo.io's organization search API,
  filtered to software/SaaS industries and small-to-mid employee counts.
  Recent-funding filtering isn't exposed cleanly by Apollo's free org search,
  so real mode still expects a `funding_notes` hint per result where available
  and otherwise leaves it for the ResearchAgent to try to confirm from the
  company's own site/press page.
"""
import csv
from dataclasses import dataclass

import requests

import config


@dataclass
class DiscoveredCompany:
    company_name: str
    website: str
    source: str
    funding_hint: str = ""


class DiscoveryAgent:
    def discover(self, limit: int = 10) -> list[DiscoveredCompany]:
        # DEMO_MODE only requires ONE of Apollo/Hunter to be set (see config.py).
        # Discovery specifically needs Apollo - if only a Hunter key was added,
        # still fall back to the seed list here rather than calling Apollo
        # with a blank key.
        if config.DEMO_MODE or not config.APOLLO_API_KEY:
            return self._discover_from_seed(limit)
        return self._discover_from_apollo(limit)

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

    def _discover_from_apollo(self, limit: int) -> list[DiscoveredCompany]:
        # Apollo requires the key in the X-Api-Key header, not the body -
        # sending it in the JSON payload (their older convention) now fails
        # with 422 INVALID_API_KEY_LOCATION.
        url = "https://api.apollo.io/v1/mixed_companies/search"
        headers = {"X-Api-Key": config.APOLLO_API_KEY, "Content-Type": "application/json"}
        payload = {
            "q_organization_keyword_tags": ["saas", "software"],
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "page": 1,
            "per_page": limit,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        out = []
        for org in data.get("organizations", [])[:limit]:
            out.append(
                DiscoveredCompany(
                    company_name=org.get("name", ""),
                    website=org.get("website_url", ""),
                    source="apollo",
                )
            )
        return out
