"""Step 4-5: identify the best point of contact and find legally-available
business contact info (name, title, company email, LinkedIn/profile URL).

Important: this agent never invents a real person's contact details. If no
provider key is configured, or a provider returns nothing, the contact fields
are left blank and marked NEEDS_ENRICHMENT so a human knows to fill them in
manually (e.g. via LinkedIn Sales Navigator, Apollo UI, or Hunter UI) rather
than being misled by fabricated data.
"""
from typing import Optional

import requests

import config
from models import Lead

NEEDS_ENRICHMENT = "NEEDS_ENRICHMENT"


class ContactFinderAgent:
    def find_contact(self, lead: Lead) -> Lead:
        if config.DEMO_MODE:
            self._mark_needs_enrichment(lead)
            return lead

        contact = self._find_via_apollo(lead) or self._find_via_hunter(lead)
        if contact:
            lead.contact_name = contact.get("name", "")
            lead.contact_title = contact.get("title", "")
            lead.contact_email = contact.get("email", "")
            lead.contact_profile_url = contact.get("linkedin_url", "")
        else:
            self._mark_needs_enrichment(lead)
        return lead

    def _mark_needs_enrichment(self, lead: Lead) -> None:
        lead.contact_name = lead.contact_name or NEEDS_ENRICHMENT
        lead.contact_title = lead.contact_title or NEEDS_ENRICHMENT
        lead.contact_email = lead.contact_email or NEEDS_ENRICHMENT
        lead.contact_profile_url = lead.contact_profile_url or NEEDS_ENRICHMENT

    def _find_via_apollo(self, lead: Lead) -> Optional[dict]:
        if not config.APOLLO_API_KEY or not lead.website:
            return None
        domain = lead.website.replace("https://", "").replace("http://", "").split("/")[0]
        url = "https://api.apollo.io/v1/mixed_people/search"
        payload = {
            "api_key": config.APOLLO_API_KEY,
            "q_organization_domains": domain,
            "person_titles": config.PREFERRED_TITLES,
            "page": 1,
            "per_page": 1,
        }
        try:
            resp = requests.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            people = resp.json().get("people", [])
        except requests.RequestException:
            return None
        if not people:
            return None
        p = people[0]
        return {
            "name": p.get("name", ""),
            "title": p.get("title", ""),
            "email": p.get("email", ""),
            "linkedin_url": p.get("linkedin_url", ""),
        }

    def _find_via_hunter(self, lead: Lead) -> Optional[dict]:
        if not config.HUNTER_API_KEY or not lead.website:
            return None
        domain = lead.website.replace("https://", "").replace("http://", "").split("/")[0]
        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": config.HUNTER_API_KEY,
            "seniority": "senior,executive",
            "limit": 1,
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            emails = resp.json().get("data", {}).get("emails", [])
        except requests.RequestException:
            return None
        if not emails:
            return None
        e = emails[0]
        name = " ".join(filter(None, [e.get("first_name"), e.get("last_name")]))
        return {
            "name": name,
            "title": e.get("position", ""),
            "email": e.get("value", ""),
            "linkedin_url": e.get("linkedin", ""),
        }
