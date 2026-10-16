"""Free contact verification: an email the company itself publishes for a founder.

An address printed on a company's own homepage / contact / about / team page,
on its own domain, whose name matches a founder (lucas@ <-> Lucas Irvine), is
about as verified as an address can be without sending mail: the company put it
there. It also costs nothing, unlike a data-provider lookup.

Generic mailboxes (hello@, info@, support@...) never count - they are not a
decision-maker. Addresses that merely *follow a pattern* seen elsewhere on the
site are not returned either; only an address that is actually published.

Only publicly published pages are read, politely (identifying User-Agent, a
handful of requests per site).
"""
import html as htmllib
import re
from typing import Optional

import requests

import storage
from agents.contact_finder import is_decision_maker

HEADERS = {"User-Agent": "SerfisLeadGenBot/0.1 (capstone project)"}
PATHS = ["", "/contact", "/about", "/team", "/company", "/about-us", "/contact-us", "/press", "/careers", "/jobs", "/legal", "/privacy",
         "/terms", "/security", "/.well-known/security.txt", "/humans.txt", "/llms.txt", "/blog"]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
GENERIC = {
    "info", "hello", "hi", "hey", "contact", "support", "help", "team", "sales", "press", "media",
    "careers", "jobs", "hiring", "admin", "office", "founders", "founder", "legal", "privacy", "security",
    "billing", "accounts", "partners", "partnerships", "marketing", "pr", "feedback", "mail", "email",
    "noreply", "no-reply", "hola", "general", "inquiries", "enquiries", "service", "demo", "bd", "ir",
}
_FILE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")


def _decode_cloudflare(hexstr: str) -> str:
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return ""


def _emails_in(page: str) -> set:
    page = htmllib.unescape(page)
    # people write "name [at] domain [dot] com" to dodge scrapers; an address they typed out is still explicit
    page = re.sub(r"\s*[\[\(]\s*at\s*[\]\)]\s*", "@", page, flags=re.I)
    page = re.sub(r"\s*[\[\(]\s*dot\s*[\]\)]\s*", ".", page, flags=re.I)
    found = set(EMAIL_RE.findall(page))
    for enc in re.findall(r'data-cfemail="([0-9a-f]+)"', page):
        found.add(_decode_cloudflare(enc))
    return {e.lower().rstrip(".") for e in found if e and not e.lower().endswith(_FILE_EXT)}


def own_domain_emails(website: str) -> set:
    """Every address on the company's own domain found on a few of its public pages."""
    host = storage.domain_of(website).split(":")[0]
    base = "https://" + host
    out = set()
    for path in PATHS:
        try:
            resp = requests.get(base + path, headers=HEADERS, timeout=8)
        except requests.RequestException:
            continue
        if resp.status_code == 200 and "text" in resp.headers.get("content-type", "text"):
            out |= _emails_in(resp.text)
    return {e for e in out if e.split("@")[-1] == host or e.split("@")[-1].endswith("." + host)}


def personal(emails: set) -> set:
    return {e for e in emails if e.split("@")[0] not in GENERIC and not e.startswith(("no-", "noreply"))}


def _local_forms(name: str) -> set:
    toks = [re.sub(r"[^a-z]", "", t) for t in name.lower().split()]
    toks = [t for t in toks if t]
    if not toks:
        return set()
    first, last = toks[0], toks[-1]
    forms = {first, f"{first}{last}", f"{first}.{last}", f"{first}_{last}", f"{first}-{last}",
             f"{first[0]}{last}", f"{first[0]}.{last}", f"{first}{last[0]}"}
    if len(toks) > 1:
        forms.add(last)
    return forms


def _parse_founders(founders: str) -> list[tuple]:
    out = []
    for line in (founders or "").splitlines():
        m = re.match(r"^(.*?)\s*(?:\((.*)\))?$", line.strip())
        if m and m.group(1):
            out.append((m.group(1).strip(), (m.group(2) or "").strip()))
    return out


def match_founder(emails: set, founders: str) -> Optional[dict]:
    """The published address belonging to the most senior decision-maker, if any."""
    best = None
    for name, title in _parse_founders(founders):
        if not is_decision_maker(title or "Founder"):
            continue
        forms = _local_forms(name)
        for e in sorted(personal(emails)):
            if e.split("@")[0] in forms:
                rank = 0 if re.search(r"ceo", title, re.I) else 1
                if best is None or rank < best[0]:
                    best = (rank, {"name": name, "title": title or "Founder", "email": e})
    return best[1] if best else None


def find_published(website: str, founders: str) -> Optional[dict]:
    """{name, title, email} for a founder whose address the company publishes, else None."""
    if not website or not founders:
        return None
    return match_founder(own_domain_emails(website), founders)
