"""Safety checks that sit between "a lead exists" and "an email goes out".

Four guardrails, all enforced where a person approves a lead (dashboard / CLI)
and again at send time (agents/send_agent.py), so none can be skipped by
accident:

1. DRAFT QUALITY   check_draft()    - unfilled placeholders, garbled wording, wrong
                                      length, asks for a call, claims the research
                                      does not support.
2. BOUNCE BREAKER  sending_block_reason() - sending pauses itself if bounces spike or
                                      anyone complains; `main.py pause` / `resume`
                                      is the manual kill switch.
3. ONE TOUCH       company_cooldown() - never email the same company twice within
                                      COMPANY_COOLDOWN_DAYS.
4. REGION          region_issues()  - outside the US (or unknown) needs a human look,
                                      because cold email rules are stricter in the
                                      EU / UK / Canada.

A flagged lead is not lost: a person can still "approve anyway" after reading the
flags. That choice is stored in lead.overrides so the sender knows it was deliberate.
"""
import email
import imaplib
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import config
import storage
from models import Lead

CATEGORIES = ("draft", "region")


# ------------------------------------------------------------------ 1. draft quality
_PLACEHOLDER = re.compile(r"\[[^\]]*\]|\{[^}]*\}|NEEDS_ENRICHMENT|\bTODO\b|lorem ipsum", re.I)
_CALL_ASK = re.compile(r"\b(call|phone|zoom|meeting|demo|calendly|calendar|schedule a)\b", re.I)
_SELF_DESCRIBE = re.compile(r"\b(autonomous|ai pipeline|ai-powered pipeline)\b", re.I)
_OFF_BRAND = re.compile(r"\bfresh creative\b", re.I)
_GARBLE_CASE = re.compile(r"\b[a-z]I\b")                      # "aI native" - case-sensitive on purpose ("AI" is fine)
_GARBLE = re.compile(r"\.\.(?!\.)|\s,|,,|\b(\w+) \1\b", re.I)
_CLAIM = re.compile(r"\d[\d,.]*\s?%|\$\s?\d[\d,.]*|\b\d+x\b|#1\b|\bguarantee[sd]?\b|\bproven\b", re.I)


def _base_name(company: str) -> str:
    return re.split(r"[\(\-–|,:]", company or "")[0].strip().lower()


def check_draft(lead: Lead) -> list:
    """Problems with the drafted email. An empty list means it is safe to approve."""
    subject, body = (lead.draft_email_subject or "").strip(), (lead.draft_email_body or "").strip()
    if not (subject and body):
        return ["there is no drafted email"]
    issues = []
    text = f"{subject}\n{body}"
    if _PLACEHOLDER.search(text):
        issues.append("contains an unfilled placeholder (brackets or NEEDS_ENRICHMENT)")
    words = len(body.split())
    if not 80 <= words <= 210:
        issues.append(f"{words} words (the approved message runs about 110 to 170)")
    if len(subject) > 90:
        issues.append("subject line is over 90 characters")
    name = (lead.contact_name or "").strip()
    if name and name.upper() != "NEEDS_ENRICHMENT" and lead.first_name().lower() not in body[:80].lower():
        issues.append(f"greeting does not use the contact's first name ({lead.first_name()})")
    base = _base_name(lead.company_name)
    if base and base not in body.lower():
        issues.append(f"never mentions the company by name ({lead.company_name})")
    m = _CALL_ASK.search(body)
    if m:
        issues.append(f"mentions '{m.group(0)}' - emails are email-only, no calls, meetings or demos")
    m = _SELF_DESCRIBE.search(body)
    if m:
        issues.append(f"describes Serfis as '{m.group(0)}' - the approved message does not")
    m = _OFF_BRAND.search(text)
    if m:
        issues.append(f"uses '{m.group(0)}' - say 'innovative advertisements' instead")
    m = _GARBLE_CASE.search(text) or _GARBLE.search(text)
    if m:
        issues.append(f"looks garbled near '{m.group(0).strip()}'")
    evidence = " ".join([lead.research_notes, lead.what_they_sell, lead.funding_notes, lead.why_it_fits]).lower()
    for claim in _CLAIM.findall(text):
        if claim.lower().strip() not in evidence:
            issues.append(f"makes a claim that is not in the research: '{claim.strip()}'")
            break
    return issues


# ------------------------------------------------------------------ 4. region
_US_STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD "
              "TN TX UT VT VA WA WV WI WY DC").split()
_USA_WORD = re.compile(r"\b(usa|u\.s\.a?|united states)\b", re.I)
_US_STATE = re.compile(r",\s*(" + "|".join(_US_STATES) + r")\b")
_US_CITIES = re.compile(r"\b(" + "|".join([
    "san francisco", "new york", "nyc", "brooklyn", "los angeles", "san diego", "san jose", "seattle", "boston", "austin", "chicago",
    "miami", "denver", "atlanta", "dallas", "houston", "palo alto", "mountain view", "menlo park", "sunnyvale", "oakland", "san mateo",
    "redwood city", "santa monica", "santa clara", "portland", "philadelphia", "pittsburgh", "boulder", "salt lake city", "nashville",
    "raleigh", "minneapolis", "detroit", "baltimore", "las vegas", "phoenix", "orlando", "tampa", "washington dc", "washington, d.c."]) + r")\b", re.I)
_STRICT = ("austria belgium bulgaria croatia cyprus czech denmark estonia finland france germany greece hungary ireland italy latvia "
           "lithuania luxembourg malta netherlands poland portugal romania slovakia slovenia spain sweden norway iceland liechtenstein "
           "switzerland canada england scotland wales").split() + ["united kingdom", "uk", "u.k."]
_STRICT_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _STRICT) + r")\b", re.I)
_STRICT_TLDS = {"de", "fr", "uk", "ca", "nl", "es", "it", "se", "dk", "fi", "ie", "at", "be", "pl", "pt", "ch", "no", "cz", "gr", "hu"}


def classify_region(location: str) -> str:
    """'us', 'strict' (EU / EEA / UK / Switzerland / Canada), 'other' or 'unknown'."""
    loc = (location or "").strip()
    if not loc:
        return "unknown"
    if _USA_WORD.search(loc):                 # explicit "USA" wins ("Denmark, WI, USA" is in Wisconsin)
        return "us"
    if _STRICT_RE.search(loc):
        return "strict"
    if _US_STATE.search(loc) or _US_CITIES.search(loc):    # "Austin, TX" or a well-known US city on its own
        return "us"
    return "other"


def region_issues(lead: Lead) -> list:
    region = classify_region(lead.location)
    if region == "us":
        return []
    if region == "strict":
        return [f"based outside the US ({lead.location}) - cold B2B email rules are stricter in the EU, UK and Canada "
                "(Germany especially); check it is allowed before sending"]
    if region == "other":
        return [f"based outside the US ({lead.location}) - confirm it is OK to email"]
    tld = storage.domain_of(lead.website).rsplit(".", 1)[-1] if lead.website else ""
    if tld in _STRICT_TLDS:
        return [f"location unknown and the website ends in .{tld} - it may be in a strict-rules country"]
    return ["location unknown - confirm the company is in the US"]


# ------------------------------------------------------------------ review + overrides
def review(lead: Lead) -> dict:
    """{'draft': [...], 'region': [...]} - empty lists mean clean."""
    return {"draft": check_draft(lead), "region": region_issues(lead)}


def acknowledged(lead: Lead) -> set:
    return {c for c in (lead.overrides or "").split(",") if c}


def blocking(lead: Lead) -> list:
    """[(category, issues)] still needing a human's OK (flagged and not yet acknowledged)."""
    seen = acknowledged(lead)
    return [(c, issues) for c, issues in review(lead).items() if issues and c not in seen]


def summary(lead: Lead) -> tuple:
    """('ok'|'flag'|'reviewed', count) for the dashboard list."""
    rev = review(lead)
    flagged = [c for c, v in rev.items() if v]
    if not flagged:
        return "ok", 0
    if all(c in acknowledged(lead) for c in flagged):
        return "reviewed", sum(len(rev[c]) for c in flagged)
    return "flag", sum(len(v) for c, v in rev.items() if v and c not in acknowledged(lead))


# ------------------------------------------------------------------ 2. pause switch + breaker
def _flag_path():
    return config.OUTPUT_DIR / "SENDING_PAUSED"


def pause(reason: str = "paused manually") -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _flag_path().write_text(f"{datetime.now(timezone.utc).isoformat()}  {reason}\n")


def resume() -> bool:
    p = _flag_path()
    if p.exists():
        p.unlink()
        return True
    return False


def pause_reason() -> Optional[str]:
    p = _flag_path()
    return p.read_text().strip() if p.exists() else None


def breaker_stats() -> dict:
    sends = storage.count_sends_since(config.BOUNCE_WINDOW_DAYS)
    bounces = storage.count_risk_events_since("bounce", config.BOUNCE_WINDOW_DAYS)
    complaints = storage.count_risk_events_since("complaint", 30)
    return {"sends": sends, "bounces": bounces, "complaints": complaints,
            "rate": (bounces / sends) if sends else 0.0}


def sending_block_reason() -> Optional[str]:
    """Why real sending must stop right now, or None. Trips (and stays tripped) automatically."""
    existing = pause_reason()
    if existing:
        return f"sending is paused: {existing.split('  ', 1)[-1]} (run `python main.py resume` once it is sorted out)"
    s = breaker_stats()
    reason = None
    if s["complaints"] >= 1:
        reason = f"{s['complaints']} spam complaint(s) in the last 30 days"
    elif s["bounces"] >= config.BOUNCE_MIN_COUNT and s["rate"] >= config.BOUNCE_RATE_PAUSE:
        reason = (f"{s['bounces']} bounces out of {s['sends']} emails in {config.BOUNCE_WINDOW_DAYS} days "
                  f"({s['rate']:.0%}, limit {config.BOUNCE_RATE_PAUSE:.0%})")
    if reason:
        pause(f"auto-paused: {reason}")
        return f"sending auto-paused: {reason}. Fix the cause, then run `python main.py resume`."
    return None


def record_bounce(address: str, reason: str = "") -> None:
    storage.log_risk_event(address, "bounce", reason)
    storage.add_suppression(address, f"bounced: {reason}"[:200])


def record_complaint(address: str, reason: str = "") -> None:
    storage.log_risk_event(address, "complaint", reason)
    storage.add_suppression(address, f"complained: {reason}"[:200])
    pause(f"spam complaint from {address}")


# ------------------------------------------------------------------ 3. one touch per company
def company_cooldown(lead: Lead) -> Optional[str]:
    """Blocks a second email to the same company within COMPANY_COOLDOWN_DAYS."""
    mine = {storage.domain_of(lead.website), storage.normalize_email(lead.contact_email).split("@")[-1]} - {"", "gmail.com"}
    for s in storage.recent_sends(config.COMPANY_COOLDOWN_DAYS):
        if s["lead_id"] == lead.id:
            continue
        theirs = {storage.domain_of(s["website"] or ""), (s["to_email"] or "").split("@")[-1]} - {"", "gmail.com"}
        if mine & theirs:
            return (f"already emailed {sorted(mine & theirs)[0]} on {s['sent_at'][:10]} "
                    f"(one touch per company every {config.COMPANY_COOLDOWN_DAYS} days)")
    return None


# ------------------------------------------------------------------ bounce detection (Gmail inbox)
def parse_bounced_recipients(raw: bytes) -> list:
    """Addresses a delivery-failure notice says could not be delivered (permanent failures only)."""
    msg = email.message_from_bytes(raw)
    out = []
    for part in msg.walk():
        if part.get_content_type() != "message/delivery-status":
            continue
        for block in part.get_payload():
            action = (block.get("Action") or "").strip().lower()
            status = (block.get("Status") or "").strip()
            rcpt = block.get("Final-Recipient") or block.get("Original-Recipient") or ""
            if action == "failed" and status.startswith("5") and ";" in rcpt:
                out.append(rcpt.split(";", 1)[1].strip().lower())
    hdr = msg.get("X-Failed-Recipients")
    if hdr and not out:
        out += [a.strip().lower() for a in hdr.split(",") if "@" in a]
    return out


def check_bounces(days: int = 7, dry_run: bool = False) -> list:
    """Scans the Gmail inbox for delivery-failure notices about emails we sent, and records them.
    Needs IMAP enabled in Gmail settings. Returns [(address, already_known)]."""
    if not config.HAS_GMAIL:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD are not set in .env.")
    sent_to = {storage.normalize_email(s["to_email"]) for s in storage.recent_sends(max(days, 30))}
    known = storage.risk_event_addresses("bounce")
    found = []
    try:
        box = imaplib.IMAP4_SSL("imap.gmail.com")
        box.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        box.select("INBOX", readonly=True)
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, data = box.search(None, f'(FROM "mailer-daemon" SINCE {since})')
        for num in (data[0] or b"").split():
            _, msgdata = box.fetch(num, "(RFC822)")
            for addr in parse_bounced_recipients(msgdata[0][1]):
                if addr in sent_to:
                    found.append((addr, addr in known))
        box.logout()
    except imaplib.IMAP4.error as exc:
        raise RuntimeError(f"Could not read the inbox ({exc}). Check that IMAP is enabled in Gmail settings.")
    for addr, was_known in found:
        if not was_known and not dry_run:
            record_bounce(addr, "delivery failure notice in inbox")
    return found
