"""Rule-based company size and industry detection from website text.

Used by the enrichment agent when Claude isn't available (and as the shared
vocabulary when it is). Deliberately conservative: it only reports a size when
the site actually states or strongly implies one, and returns "" otherwise,
so downstream steps fall back to default behavior instead of acting on a guess.
"""
import re
from typing import Optional

SIZE_BANDS = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]

# label -> keywords. A label needs at least two DISTINCT keyword hits to win.
INDUSTRIES: dict[str, list[str]] = {
    "E-commerce / Retail": ["add to cart", "shop now", "free shipping", "checkout", "shop all",
                            "new arrivals", "best sellers", "gift card", "returns policy", "our products"],
    "Fashion / Beauty / Lifestyle": ["apparel", "clothing", "skincare", "beauty", "jewelry", "fashion",
                                     "wardrobe", "cosmetics", "streetwear", "outfit"],
    "Food & Beverage": ["restaurant", "menu", "coffee", "recipe", "catering", "brewery", "bakery",
                        "snacks", "beverage", "organic food"],
    "Health / Fitness / Wellness": ["fitness", "wellness", "gym", "nutrition", "yoga", "clinic",
                                    "patients", "supplements", "workout", "therapy"],
    "Travel / Hospitality": ["hotel", "resort", "vacation", "tours", "travel", "bookings", "getaway",
                             "destinations", "stay with us"],
    "Media / Entertainment": ["podcast", "streaming", "film", "music", "games", "gaming", "studio",
                              "episodes", "creators"],
    "Education": ["students", "courses", "curriculum", "university", "tutoring", "classroom",
                  "learners", "bootcamp"],
    "Real Estate": ["real estate", "properties", "homes for sale", "realtor", "listings", "mortgage",
                    "tenants", "leasing"],
    "Finance / Insurance": ["insurance", "lending", "loans", "investment", "fintech", "payments",
                            "banking", "wealth", "credit"],
    "Marketing / Agency": ["digital marketing", "advertising agency", "seo", "branding agency",
                           "creative agency", "social media management", "ad campaigns", "media buying"],
    "IT Services / Dev Agency": ["software development", "custom software", "outsourcing",
                                 "digital transformation", "development company", "it consulting",
                                 "software engineering", "dedicated team", "staff augmentation"],
    "HR / Recruiting": ["recruiting", "recruiter", "hiring", "job seekers", "remote jobs", "talent",
                        "job board", "candidates", "staffing"],
    "Software / SaaS": ["saas", "book a demo", "free trial", "integrations", "dashboard", "api",
                        "workflow", "software platform", "per user", "request a demo"],
}

CONSUMER = {"E-commerce / Retail", "Fashion / Beauty / Lifestyle", "Food & Beverage",
            "Health / Fitness / Wellness", "Travel / Hospitality", "Media / Entertainment"}
B2B = {"Software / SaaS", "IT Services / Dev Agency", "Marketing / Agency",
       "HR / Recruiting", "Finance / Insurance"}


def industry_group(label: str) -> str:
    """'consumer', 'b2b' or 'other' for an industry label (any free text)."""
    text = (label or "").lower()
    if any(k in text for k in ("e-commerce", "ecommerce", "retail", "dtc", "apparel", "fashion",
                               "beauty", "food", "beverage", "fitness", "wellness", "travel",
                               "hospitality", "entertainment", "consumer")):
        return "consumer"
    if any(k in text for k in ("software", "saas", "it services", "agency", "marketing",
                               "recruit", "hr ", "finance", "insurance", "b2b", "technology")):
        return "b2b"
    return "other"


def classify_industry(text: str) -> str:
    lowered = (text or "").lower()
    best_label, best_hits = "", 1
    for label, words in INDUSTRIES.items():
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", lowered))
        if hits > best_hits:
            best_label, best_hits = label, hits
    return best_label


def band_for(n: int) -> str:
    for limit, band in ((10, "1-10"), (50, "11-50"), (200, "51-200"), (500, "201-500"), (1000, "501-1000")):
        if n <= limit:
            return band
    return "1000+"


_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)"
_STAFF = r"(?:full[- ]time )?(?:employees|team members|teammates|staff|colleagues)"
_SIZE_PATTERNS = [
    rf"{_NUM}\s*[-\u2013]\s*{_NUM}\s+{_STAFF}",                       # 50-100 employees
    rf"(?:over|more than|approximately|about|around|nearly|\+)?\s*{_NUM}\s*\+?\s+{_STAFF}",  # 250+ employees
    rf"team of (?:over |more than |around |about |nearly )?{_NUM}",   # team of 40
    rf"{_NUM}[- ](?:person|strong) team",                              # 12-person team
]
# Looser nouns ("450 professionals") only count with company-ish wording just
# before them, no customer/community wording, and a plausible staff size -
# otherwise "trusted by 2,000 professionals" or "a community of 5,000
# engineers" would be read as headcount.
_LOOSE = rf"{_NUM}\s*\+?\s+(?:professionals|engineers|developers|experts|specialists|consultants)"
_COMPANYISH = ("our ", "we ", "we're", "with ", "team", "employ", "staff", "offices", "centers", "centres", "across")
_NOT_STAFF = ("community", "network", "marketplace", "talent pool", "join", "trusted by", "customers",
              "clients", "users", "members of", "businesses", "companies")


def estimate_size_label(text: str) -> str:
    """Employee-count band if the text states one, else ''."""
    lowered = (text or "").lower()
    counts = []
    for pattern in _SIZE_PATTERNS:
        for m in re.finditer(pattern, lowered):
            nums = [int(g.replace(",", "")) for g in m.groups() if g and g.replace(",", "").isdigit()]
            if nums:
                counts.append(max(nums))
    for m in re.finditer(_LOOSE, lowered):
        before = lowered[max(0, m.start() - 70):m.start()]
        n = int(m.group(1).replace(",", ""))
        if n <= 3000 and any(w in before for w in _COMPANYISH) and not any(w in before for w in _NOT_STAFF):
            counts.append(n)
    counts = [c for c in counts if 1 <= c <= 2_000_000]
    if counts:
        return band_for(max(counts))
    if re.search(r"\b(solo founder|one-person|solopreneur)\b", lowered):
        return "1-10"
    return ""
