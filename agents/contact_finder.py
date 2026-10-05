"""Step 4-5: identify the best point of contact and find legally-available
business contact info (name, title, company email, LinkedIn/profile URL).

Only DECISION MAKERS count: a founder/owner/CEO/president, a chief/VP/head/
director, or a manager of a marketing-type function (Marketing Manager, Social
Media Manager...). Generic mailboxes (info@, contact@) and people without
authority (associates, coordinators, specialists, analysts, engineers, managers
of unrelated functions...) are never returned - the orchestrator cancels the
company instead. Named people come from the Actor's
paid "business leads" add-on (output field `leadsEnrichment`), see config.py.

Important: this agent never invents a real person's contact details. If no
provider key is configured, or a provider returns nothing, the contact fields
are left blank and marked NEEDS_ENRICHMENT so a human knows to fill them in
manually (e.g. via LinkedIn Sales Navigator or the Apify Console)
rather than being misled by fabricated data.

Contact-finding uses config.APIFY_CONTACT_ACTOR (default
vdrmota/contact-info-scraper) - a well-established Apify Actor (60K+ users)
that only extracts what a company has published on its own site (contact/
about pages). It does not scrape LinkedIn profiles for this data - a
deliberate choice, see README "Ethical/legal notes on contact data".
"""
import re
from typing import Optional

import requests

import config
from agents import classify
from agents.apify_client import run_actor
from models import Lead

NEEDS_ENRICHMENT = "NEEDS_ENRICHMENT"


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(rf"(?<![a-z]){p}(?![a-z])", text) for p in patterns)


def _normalize(title: str) -> str:
    return " ".join((title or "").lower().replace("&", " and ").replace("/", " ").split())


def is_decision_maker(title: str) -> bool:
    """True if the job title carries authority to make a buying decision."""
    t = _normalize(title)
    if not t or _any(config.NOT_AUTHORITY_PATTERNS, t):
        return False
    if _any(config.AUTHORITY_TITLE_PATTERNS, t):
        return True
    return _any([r"manager"], t) and _any(config.MANAGER_FUNCTION_PATTERNS, t)


_SENIOR = [r"chief", r"c[a-z]o", r"vp", r"vice president", r"head of", r"director"]
_TOP = [r"co-?founder", r"founder", r"owner", r"ceo", r"president",
        r"managing director", r"general manager"]


def _rank(title: str, tier: str = "unknown", group: str = "other") -> tuple:
    """Lower is better: (how senior/right the role is for this company size,
    then a nudge toward the roles this kind of industry buys through).

    Tiny companies: the founder/CEO decides. Small and unknown-size ones
    (typical for startups): marketing/growth leaders first if they exist, then
    the founder/CEO, then marketing managers. Mid-size and up: marketing
    leaders, then marketing managers, then founder/CEO.
    """
    t = _normalize(title)
    relevant = _any(config.RELEVANT_TITLE_PATTERNS, t)
    senior = relevant and _any(_SENIOR, t)
    manager = relevant and _any([r"manager"], t)
    top = _any(_TOP, t)
    if tier == "micro":
        order = [top, senior, manager]
    elif tier in ("small", "unknown"):
        order = [senior, top, manager]
    else:
        order = [senior, manager, top]
    primary = next((i for i, hit in enumerate(order) if hit), 3)
    prefs = config.INDUSTRY_TITLE_PREFS.get(group, [])
    return primary, 0 if prefs and _any(prefs, t) else 1


class ContactFinderAgent:
    def find_contact(self, lead: Lead) -> Lead:
        if config.DEMO_MODE:
            self._mark_needs_enrichment(lead)
            return lead

        contact = self._find_via_apify(lead)
        if contact:
            lead.contact_name = contact.get("name", "")
            lead.contact_title = contact.get("title", "")
            lead.contact_email = contact.get("email", "")
            lead.contact_profile_url = contact.get("linkedin_url", "")
        # Fills in NEEDS_ENRICHMENT for any field still blank - covers both
        # "no contact found at all" and "found an email but no name/title"
        # (e.g. the free tier of the Apify contact-finder, which returns
        # emails/LinkedIn but not named leads unless the paid add-on is on).
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
        # One page is enough: we only use the named people from the leads
        # add-on, not emails scraped off the site (those are usually generic).
        run_input = {
            "startUrls": [{"url": website}],
            "maxDepth": 0,
            "sameDomain": True,
            "maxRequests": 1,
            "maximumLeadsEnrichmentRecords": config.APIFY_LEADS_PER_DOMAIN,
            "leadsEnrichmentDepartments": config.APIFY_DEPARTMENTS_BY_TIER.get(
                lead.size_tier(), config.APIFY_DEPARTMENTS_BY_TIER["unknown"]),
        }
        try:
            items = run_actor(config.APIFY_CONTACT_ACTOR, run_input,
                              max_charge_usd=config.APIFY_CONTACT_MAX_CHARGE_USD)
        except requests.RequestException:
            return None
        return self._best_decision_maker(
            items, tier=lead.size_tier(), group=classify.industry_group(lead.industry)
        )

    def _best_decision_maker(self, items: list[dict], tier: str = "unknown",
                             group: str = "other") -> Optional[dict]:
        """Picks the best decision maker for this company's size and industry
        who has an email, or None."""
        best = None
        for item in items:
            for person in item.get("leadsEnrichment") or []:
                email = (person.get("email") or "").strip()
                title = (person.get("jobTitle") or "").strip()
                if "@" not in email or not is_decision_maker(title):
                    continue
                rank = _rank(title, tier, group)
                if best is None or rank < best[0]:
                    best = (rank, person)
        if best is None:
            return None
        person = best[1]
        name = person.get("fullName") or " ".join(
            filter(None, [person.get("firstName"), person.get("lastName")])
        )
        return {
            "name": name,
            "title": person.get("jobTitle", ""),
            "email": person["email"].strip(),
            "linkedin_url": person.get("linkedinProfile") or "",
        }
