"""Step 4-5: identify the best point of contact and find legally-available
business contact info (name, title, company email, LinkedIn/profile URL).

Important: this agent never invents a real person's contact details. If no
provider key is configured, or a provider returns nothing, the contact fields
are left blank and marked NEEDS_ENRICHMENT so a human knows to fill them in
manually (e.g. via LinkedIn Sales Navigator, Apify Console, or Hunter UI)
rather than being misled by fabricated data.

Contact-finding uses config.APIFY_CONTACT_ACTOR (default
vdrmota/contact-info-scraper) - a well-established Apify Actor (60K+ users)
that only extracts what a company has published on its own site (contact/
about pages). It does not scrape LinkedIn profiles for this data - a
deliberate choice, see README "Ethical/legal notes on contact data".
"""
from typing import Optional

import requests

import config
from agents.apify_client import run_actor
from models import Lead

NEEDS_ENRICHMENT = "NEEDS_ENRICHMENT"


class ContactFinderAgent:
    def find_contact(self, lead: Lead) -> Lead:
        if config.DEMO_MODE:
            self._mark_needs_enrichment(lead)
            return lead

        contact = self._find_via_apify(lead) or self._find_via_hunter(lead)
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

    def _find_via_apify(self, lead: Lead) -> Optional[dict]:
        if not config.APIFY_API_TOKEN or not lead.website:
            return None
        website = lead.website if lead.website.startswith("http") else f"https://{lead.website}"
        run_input = {
            "startUrls": [{"url": website}],
            "maxDepth": 1,
            "sameDomain": True,
            "maxRequests": 10,
        }
        try:
            items = run_actor(config.APIFY_CONTACT_ACTOR, run_input)
        except requests.RequestException:
            return None
        for item in items:
            contact = self._parse_result(item)
            if contact:
                return contact
        return None

    def _parse_result(self, item: dict) -> Optional[dict]:
        """Defensive parsing - checks likely field-name variants since the
        exact output schema wasn't fully confirmed before this was written.
        Only returns a result if we found at least an email - a name/title
        with no email isn't independently useful here."""
        emails = item.get("emails") or item.get("email") or []
        if isinstance(emails, str):
            emails = [emails]
        if not emails:
            return None

        leads = item.get("leads") or item.get("employees") or []
        name, title = "", ""
        if leads:
            first_lead = leads[0]
            name = first_lead.get("name", "") or " ".join(
                filter(None, [first_lead.get("firstName"), first_lead.get("lastName")])
            )
            title = first_lead.get("title") or first_lead.get("jobTitle") or ""

        linkedins = item.get("linkedIns") or item.get("linkedin") or []
        linkedin_url = linkedins[0] if linkedins else ""

        return {
            "name": name,
            "title": title,
            "email": emails[0],
            "linkedin_url": linkedin_url,
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
