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
        # Apollo requires the key in the X-Api-Key header, not the body - see
        # the matching note in discovery.py's _discover_from_apollo. Apollo
        # also renamed this endpoint from mixed_people/search to
        # mixed_people/api_search at some point after this was first written.
        headers = {"X-Api-Key": config.APOLLO_API_KEY, "Content-Type": "application/json"}
        search_payload = {
            "q_organization_domains": domain,
            "person_titles": config.PREFERRED_TITLES,
            "page": 1,
            "per_page": 1,
        }
        try:
            resp = requests.post(
                "https://api.apollo.io/v1/mixed_people/api_search",
                json=search_payload, headers=headers, timeout=20,
            )
            resp.raise_for_status()
            people = resp.json().get("people", [])
        except requests.RequestException:
            return None
        if not people:
            return None

        # The search endpoint only returns a masked preview (first name, a
        # hidden last name, has_email/has_direct_phone flags) - it never
        # includes the actual email. Getting the real email requires a
        # second call, to the enrichment ("match") endpoint, which spends
        # one Apollo credit. See https://docs.apollo.io/reference/people-enrichment
        candidate = people[0]
        return self._enrich_via_apollo_match(candidate) or {
            "name": candidate.get("first_name", ""),
            "title": candidate.get("title", ""),
            "email": "",
            "linkedin_url": "",
        }

    def _enrich_via_apollo_match(self, candidate: dict) -> Optional[dict]:
        headers = {"X-Api-Key": config.APOLLO_API_KEY, "Content-Type": "application/json"}
        payload = {"id": candidate.get("id"), "reveal_personal_emails": True}
        try:
            resp = requests.post(
                "https://api.apollo.io/v1/people/match",
                json=payload, headers=headers, timeout=20,
            )
            resp.raise_for_status()
            person = resp.json().get("person")
        except requests.RequestException:
            return None
        if not person:
            return None
        name = " ".join(filter(None, [person.get("first_name"), person.get("last_name")]))
        return {
            "name": name,
            "title": person.get("title", ""),
            "email": person.get("email", ""),
            "linkedin_url": person.get("linkedin_url", ""),
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
