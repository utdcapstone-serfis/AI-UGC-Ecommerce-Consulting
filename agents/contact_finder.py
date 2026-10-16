"""Step 4-5: identify the best point of contact and find legally-available
business contact info (name, title, company email, LinkedIn/profile URL).

Only DECISION MAKERS count: a founder/owner/CEO/president, a chief/VP/head/
director, or a manager of a marketing-type function (Marketing Manager, Social
Media Manager...). Generic mailboxes (info@, contact@) and people without
authority (associates, coordinators, specialists, analysts, engineers, managers
of unrelated functions...) are never returned - the orchestrator cancels the
company instead. Named people come from the Actor's
paid "business leads" add-on (output field `leadsEnrichment`), see config.py.

Important: an address Apify returns is real. When it returns nobody, the agent
may fall back to first@domain for a YC founder (config.GUESS_FOUNDER_EMAILS);
that address is flagged email_status="guessed" and cannot be sent until a
human confirms it. Otherwise this agent never invents contact details. If no
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
import storage
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
    def __init__(self):
        self.errors: list[str] = []   # lookups that failed outright (not "no email found")
        self.last_outcome = ""        # hit | miss | unverified | error - read by the orchestrator
        self.paid_lookups = 0         # Apify contact lookups actually made
        self.verifier_cost_usd = 0.0

    def find_contact(self, lead: Lead) -> Lead:
        lead = self._locate_contact(lead)
        return self._enforce(lead)

    def _reject(self, lead: Lead, reason: str, transient: bool = False) -> Lead:
        """The contact did not pass verification: clear it so the company is dropped, and say why."""
        lead.contact_name = lead.contact_title = lead.contact_email = lead.contact_profile_url = ""
        lead.email_status = lead.contact_check = ""
        self._mark_needs_enrichment(lead)
        self.errors.append(f"{lead.company_name}: contact not verified - {reason}")
        # A broken or rate-limited tool says nothing about the company, so it is not remembered as a verdict.
        self.last_outcome = "error" if transient else "unverified"
        return lead

    def _enforce(self, lead: Lead) -> Lead:
        """A lead only keeps a contact that is verified: published by the company (or human-confirmed)
        and, when LINKEDIN_VERIFY is on, a current decision-making role on LinkedIn."""
        if config.DEMO_MODE or not lead.has_email():
            return lead
        if config.REQUIRE_VERIFIED_CONTACT and lead.email_status not in config.VERIFIED_EMAIL_STATUSES:
            return self._reject(lead, f"email is '{lead.email_status or 'unverified'}'; only an address the company publishes, "
                                      "or one a person confirmed, counts")
        checks = []
        if lead.email_status == "published":
            checks.append(f"email published on {storage.domain_of(lead.website)}")
        elif lead.email_status == "linkedin":
            checks.append("email written on the founder's own LinkedIn profile")
        if config.LINKEDIN_VERIFY and lead.email_status != "confirmed":
            from agents import linkedin                                 # lazy: linkedin imports this module
            ok, why, details = linkedin.check_contact(lead)
            if not ok:
                return self._reject(lead, why, transient=bool(details.get("transient")))
            checks.append(f"LinkedIn: {why}")
            lead.contact_title = details.get("title") or lead.contact_title
            lead.contact_profile_url = details.get("url") or lead.contact_profile_url
            if not (lead.location or "").strip() and details.get("place"):
                lead.location = details["place"]
        elif lead.email_status == "confirmed":
            checks.append("confirmed by a person")
        lead.contact_check = "; ".join(checks)
        return lead

    def _locate_contact(self, lead: Lead) -> Lead:
        if config.DEMO_MODE:
            self._mark_needs_enrichment(lead)
            return lead

        # 1) Free: an address the company itself publishes for a founder.
        if lead.email_status in ("published", "linkedin") and lead.contact_email:
            self.last_outcome = "hit"
            return lead
        from agents import site_emails          # lazy: site_emails imports this module
        published = site_emails.find_published(lead.website, lead.founders)
        if published:
            lead.contact_name, lead.contact_title = published["name"], published["title"]
            lead.contact_email, lead.email_status = published["email"], "published"
            lead.contact_profile_url = lead.contact_profile_url or ""
            self.last_outcome = "hit"
            self._mark_needs_enrichment(lead)
            return lead
        # 1b) An email the founder wrote on their own LinkedIn profile (never a guess).
        if config.LINKEDIN_EMAILS and config.APIFY_API_TOKEN:
            from agents import linkedin
            hit = linkedin.find_explicit_email(lead)
            if hit:
                lead.contact_name, lead.contact_title = hit["name"], hit["title"]
                lead.contact_email, lead.email_status = hit["email"], "linkedin"
                lead.contact_profile_url = hit["linkedin"]
                self.last_outcome = "hit"
                self._mark_needs_enrichment(lead)
                return lead
        # 2) Paid, optional: Apify's contact add-on.
        if not config.PAID_LOOKUP_FALLBACK:
            self.last_outcome = "miss"
            self._mark_needs_enrichment(lead)
            return lead
        contact = self._find_via_apify(lead)
        if contact:
            lead.contact_name = contact.get("name", "")
            lead.contact_title = contact.get("title", "")
            lead.contact_email = contact.get("email", "")
            lead.contact_profile_url = contact.get("linkedin_url", "")
            lead.email_status = "found" if lead.contact_email else ""
        elif config.GUESS_FOUNDER_EMAILS:
            self._guess_from_founders(lead)
        # Fills in NEEDS_ENRICHMENT for any field still blank - covers both
        # "no contact found at all" and "found an email but no name/title"
        # (e.g. the free tier of the Apify contact-finder, which returns
        # emails/LinkedIn but not named leads unless the paid add-on is on).
        self._mark_needs_enrichment(lead)
        return lead

    @staticmethod
    def _guess_from_founders(lead: Lead) -> None:
        """first@domain for the most senior founder on the YC profile - a guess."""
        domain = re.sub(r"^https?://(www\.)?", "", (lead.website or "").lower()).split("/")[0]
        if not domain or "." not in domain:
            return
        people = []
        for line in (lead.founders or "").splitlines():
            m = re.match(r"^(.*?)\s*(?:\((.*)\))?$", line.strip())
            if m and m.group(1):
                people.append((m.group(1).strip(), (m.group(2) or "").strip()))
        people = [p for p in people if is_decision_maker(p[1] or "Founder")]
        if not people:
            return
        people.sort(key=lambda p: 0 if re.search(r"ceo", p[1], re.I) else 1)
        name, title = people[0]
        first = re.sub(r"[^a-z]", "", name.split()[0].lower()) if name.split() else ""
        if not first:
            return
        lead.contact_name, lead.contact_title = name, title or "Founder"
        lead.contact_email = f"{first}@{domain}"
        lead.email_status = "guessed"

    def _mark_needs_enrichment(self, lead: Lead) -> None:
        lead.contact_name = lead.contact_name or NEEDS_ENRICHMENT
        lead.contact_title = lead.contact_title or NEEDS_ENRICHMENT
        lead.contact_email = lead.contact_email or NEEDS_ENRICHMENT
        lead.contact_profile_url = lead.contact_profile_url or NEEDS_ENRICHMENT

    def _find_via_apify(self, lead: Lead) -> Optional[dict]:
        self.last_outcome = ""
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
        self.paid_lookups += 1
        try:
            items = run_actor(config.APIFY_CONTACT_ACTOR, run_input,
                              max_charge_usd=config.APIFY_CONTACT_MAX_CHARGE_USD)
        except requests.RequestException as exc:
            # A failed lookup is not the same as "no email exists" - record it
            # so the run report can tell the two apart.
            resp = getattr(exc, "response", None)
            detail = ""
            if resp is not None:
                try:
                    detail = resp.json().get("error", {}).get("message", "")
                except ValueError:
                    detail = ""
            self.errors.append(f"{lead.company_name}: {detail or type(exc).__name__}")
            self.last_outcome = "error"
            return None
        contact = self._best_decision_maker(
            items, tier=lead.size_tier(), group=self._group(lead)
        )
        if contact is None:
            self.last_outcome = "miss"
            return None
        ok, why = self._verify(contact["email"], website)
        if not ok:
            self.last_outcome = "unverified"
            self.errors.append(f"{lead.company_name}: {contact['email']} rejected - {why}")
            return None
        self.last_outcome = "hit"
        return contact

    def _verify(self, email: str, website: str) -> tuple:
        """The gate every address must pass: it is on the company's own domain, and
        a mail-server check does not call it invalid. (A catch-all domain - e.g. most
        Google Workspace setups - can only ever come back 'risky'; that is accepted,
        because the address came from a provider for a named decision-maker.)"""
        host = storage.domain_of(website).split(":")[0]
        edomain = email.split("@")[-1].lower()
        if not (edomain == host or edomain.endswith("." + host) or host.endswith("." + edomain)):
            return False, f"domain {edomain} is not the company's domain ({host})"
        try:
            items = run_actor(config.EMAIL_VERIFIER_ACTOR, {"emailList": [email]}, max_charge_usd=0.5)
        except requests.RequestException:
            return False, "verifier unavailable"
        self.verifier_cost_usd += 0.0012
        if not items:
            return False, "verifier returned nothing"
        v, chk, cls = (items[0].get("verdict") or {}), (items[0].get("checks") or {}), (items[0].get("classification") or {})
        if cls.get("isDisposable"):
            return False, "disposable address"
        if v.get("status") in ("invalid", "undeliverable", "bad") or not chk.get("syntaxValid", True) \
                or not chk.get("mxRecordsValid", True):
            return False, f"verifier says {v.get('status') or 'invalid'}"
        return True, v.get("status") or "ok"

    @staticmethod
    def _group(lead: Lead) -> str:
        """consumer / b2b / other - the tracker's market wins over a guess from industry text."""
        market = (lead.market or "").lower()
        if market.startswith("b2c"):
            return "consumer"
        if market.startswith("b2b"):
            return "b2b"
        return classify.industry_group(lead.industry)

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
