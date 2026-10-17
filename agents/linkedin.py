"""LinkedIn role check: is this founder real, and do they still hold the role?

Used only as a SECOND check on top of the website rule. An email is only ever
accepted when the company publishes it itself (agents/site_emails.py); LinkedIn
never supplies or guesses an address. We run the profile actor in its "no email"
mode, so it does not even search for one, and ignore any email field it returns.

What it confirms (about $0.005 per profile through Apify):
- the person on the YC page is a real LinkedIn profile whose name matches,
- their CURRENT position (no end date) is at this company,
- that position is a decision-making role (founder, CEO, CTO, chief, head...),
and it gives us the profile's country, which fills in a missing location.

Reading public LinkedIn pages goes against LinkedIn's terms of service even without
logging in; it is used here narrowly, for a role check only, never for contact data.
"""
import difflib
import re
from typing import Optional

import requests

import config
import storage
from agents import yc
from agents.apify_client import run_actor


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _base_company(name: str) -> str:
    return _norm(re.split(r"[\(\-–|,:]", name or "")[0])


def find_linkedin_url(lead) -> str:
    """The contact's LinkedIn link: already on the lead, else from the YC founder list."""
    if "linkedin.com/in/" in (lead.contact_profile_url or ""):
        return lead.contact_profile_url
    profile = yc.fetch_profile(lead.yc_profile_url) if lead.yc_profile_url else None
    if not profile:
        return ""
    want = _norm(lead.contact_name)
    first = _norm((lead.contact_name or "").split()[0]) if lead.contact_name else ""
    for f in profile["founders"]:
        if f.get("linkedin") and (_norm(f["name"]) == want or (first and _norm(f["name"].split()[0]) == first)):
            return f["linkedin"]
    return ""


_CACHE: dict = {}
paid_reads = 0          # profiles actually fetched from Apify this process (each ~$0.005)
_blocked = ""           # set when the actor reports a plan/rate limit, so we stop calling it and say why


def _username(url: str) -> str:
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url or "")
    return m.group(1) if m else ""


def _normalize(item: dict) -> dict:
    """Both supported actors -> one shape (firstName, headline, about, location, currentPosition, experience).
    The actors' own email fields are deliberately dropped: they are guesses, not what the person wrote."""
    if "basic_info" in item:                                   # apimaestro/linkedin-profile-detail
        b, loc = item.get("basic_info") or {}, (item.get("basic_info") or {}).get("location") or {}
        exp = item.get("experience") or []
        return {
            "firstName": b.get("first_name"), "lastName": b.get("last_name"), "headline": b.get("headline"), "about": b.get("about"),
            "linkedinUrl": b.get("profile_url"),
            "location": {"countryCode": loc.get("country_code"), "linkedinText": loc.get("full"), "parsed": {"text": loc.get("full")}},
            "currentPosition": [{"position": e.get("title"), "companyName": e.get("company"), "companyUniversalName": "",
                                 "endDate": {"text": "Present"}} for e in exp if e.get("is_current")],
            "experience": [{"title": e.get("title"), "description": e.get("description")} for e in exp],
        }
    item = dict(item)                                          # harvestapi/linkedin-profile-scraper
    item.pop("emails", None)
    return item


def fetch_profile(url: str) -> Optional[dict]:
    """One LinkedIn profile via Apify, cached so a profile is never paid for twice in a run.
    Raises RuntimeError with the actor's own message when it refuses (plan limit, private profile...)."""
    global paid_reads, _blocked
    key = (url or "").rstrip("/").lower()
    if key in _CACHE:
        return _CACHE[key]
    if _blocked:
        raise RuntimeError(_blocked)
    paid_reads += 1
    if "apimaestro" in config.LINKEDIN_ACTOR:
        run_input = {"username": _username(url), "includeEmail": False}
    else:
        run_input = {"profileScraperMode": config.LINKEDIN_MODE, "urls": [url]}
    items = run_actor(config.LINKEDIN_ACTOR, run_input, max_charge_usd=0.1)
    first = items[0] if items else {}
    if not items or not (first.get("firstName") or first.get("basic_info")):
        # a refusal arrives as an item with "error" or "message" (daily/plan limits, private or missing profile)
        msg = str(first.get("error") or first.get("message") or "the actor returned nothing")
        if re.search(r"limit|upgrade|quota|plan|wait until", msg, re.I):
            _blocked = f"LinkedIn tool unavailable: {msg}"
        raise RuntimeError(msg)
    _CACHE[key] = _normalize(first)
    return _CACHE[key]


def explicit_emails(profile: dict) -> list:
    """Addresses the person wrote ON their profile (headline, About, role descriptions, websites text).
    Deliberately ignores profile["emails"]: that field is the actor's own email finder (pattern guesses)."""
    from agents import site_emails                    # lazy: site_emails imports contact_finder
    parts = [profile.get("headline"), profile.get("about")]
    for key in ("experience", "projects", "services", "featured"):
        for item in (profile.get(key) or []):
            if isinstance(item, dict):
                parts += [item.get("description"), item.get("title"), item.get("text")]
    found = site_emails._emails_in(" ".join(str(p) for p in parts if p))
    return sorted(site_emails.personal(found))


def find_explicit_email(lead, max_founders: int = 2) -> Optional[dict]:
    """First founder (CEO first) whose LinkedIn profile explicitly lists an email.
    Returns {name, title, email, linkedin} or None. Never guesses."""
    from agents.contact_finder import is_decision_maker
    profile = yc.fetch_profile(lead.yc_profile_url) if lead.yc_profile_url else None
    founders = [f for f in (profile or {}).get("founders", []) if f.get("linkedin") and is_decision_maker(f.get("title") or "Founder")]
    founders.sort(key=lambda f: 0 if re.search(r"ceo", f.get("title") or "", re.I) else 1)
    for f in founders[:max_founders]:
        try:
            data = fetch_profile(f["linkedin"])
        except (requests.RequestException, RuntimeError):
            continue
        mails = explicit_emails(data or {})
        if mails:
            return {"name": f["name"], "title": f.get("title") or "Founder", "email": mails[0], "linkedin": f["linkedin"]}
    return None


def verify_role(profile: dict, lead) -> tuple:
    """(ok, reason, details). Pure function so it can be tested without any network call."""
    from agents.contact_finder import is_decision_maker       # lazy: contact_finder imports this module
    if not profile or not (profile.get("firstName") or profile.get("lastName")):
        return False, "LinkedIn returned no profile", {"transient": True}      # says nothing about the company
    full = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    expected = (lead.contact_name or "").strip()
    if expected and difflib.SequenceMatcher(None, _norm(full), _norm(expected)).ratio() < 0.75 \
            and _norm(full.split()[0])[:4] != _norm(expected.split()[0])[:4]:
        return False, f"LinkedIn profile is for '{full}', not '{expected}'", {}
    company = _base_company(lead.company_name)
    domain_label = _norm(storage.domain_of(lead.website).split(".")[0])
    current = [p for p in (profile.get("currentPosition") or [])
               if not (p.get("endDate") or {}).get("text") or (p.get("endDate") or {}).get("text", "").lower() == "present"]
    details = {"name": full, "country": ((profile.get("location") or {}).get("countryCode") or ""),
               "place": ((profile.get("location") or {}).get("parsed") or {}).get("text") or (profile.get("location") or {}).get("linkedinText") or "",
               "url": profile.get("linkedinUrl") or "", "headline": profile.get("headline") or ""}
    for pos in current:
        cname, slug = _norm(pos.get("companyName")), _norm(pos.get("companyUniversalName"))
        same = bool(company) and (
            (cname and (company in cname or cname in company)) or (slug and (company in slug or slug in company))
            or (slug and domain_label and (slug in domain_label or domain_label in slug)))
        if same:
            title = pos.get("position") or ""
            if not is_decision_maker(title):
                return False, f"LinkedIn title '{title}' is not a decision-making role", details
            details["title"] = title
            return True, f"confirmed {title} at {pos.get('companyName')} (current)", details
    held = ", ".join(f"{p.get('position')} at {p.get('companyName')}" for p in current) or "no current position listed"
    return False, f"LinkedIn does not show a current role at {lead.company_name} ({held})", details


def check_contact(lead) -> tuple:
    """Full check for a lead's contact. Fails closed: no LinkedIn link, or an actor error, means not verified."""
    url = find_linkedin_url(lead)
    if not url:
        return False, "no LinkedIn link on the YC page to check", {}
    try:
        profile = fetch_profile(url)
    except (requests.RequestException, RuntimeError) as exc:
        return False, f"LinkedIn lookup failed: {str(exc)[:140] or type(exc).__name__}", {"transient": True}
    ok, why, details = verify_role(profile, lead)
    return ok, why, details
