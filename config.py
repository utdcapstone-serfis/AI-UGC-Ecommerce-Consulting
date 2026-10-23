"""Central configuration loaded from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = OUTPUT_DIR / "leads.db"
SEED_COMPANIES_CSV = DATA_DIR / "seed_companies.csv"
WATCHLIST_CSV = DATA_DIR / "target_companies.csv"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Outbound email via Gmail SMTP. Needs a Google "app password" (16 characters),
# not the normal account password. Google displays it in groups of four with
# spaces; the spaces are stripped here.
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
HAS_GMAIL = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)

# Sending guardrails (agents/send_agent.py). MAILING_ADDRESS goes in every
# email footer; CAN-SPAM requires a physical postal address, so real (non-test)
# sends are refused until it is set.
MAILING_ADDRESS = os.getenv("MAILING_ADDRESS", "").strip()
EMAIL_DAILY_CAP = int(os.getenv("EMAIL_DAILY_CAP", "20"))
EMAIL_SEND_DELAY_SECONDS = int(os.getenv("EMAIL_SEND_DELAY_SECONDS", "45"))

# Guardrails (agents/guardrails.py)
BOUNCE_WINDOW_DAYS = int(os.getenv("BOUNCE_WINDOW_DAYS", "14"))       # look-back for the bounce breaker
BOUNCE_MIN_COUNT = int(os.getenv("BOUNCE_MIN_COUNT", "2"))           # never trip on a single bounce
BOUNCE_RATE_PAUSE = float(os.getenv("BOUNCE_RATE_PAUSE", "0.05"))    # pause sending at this bounce rate
COMPANY_COOLDOWN_DAYS = int(os.getenv("COMPANY_COOLDOWN_DAYS", "90"))  # one email per company per this many days

# Apify Actor ids used for discovery and contact-finding (see
# agents/discovery.py and agents/contact_finder.py). Overridable via .env in
# case you want to swap in a different Actor without touching code.
APIFY_DISCOVERY_ACTOR = os.getenv(
    "APIFY_DISCOVERY_ACTOR", "compass/crawler-google-places"
)
APIFY_CONTACT_ACTOR = os.getenv("APIFY_CONTACT_ACTOR", "vdrmota/contact-info-scraper")

# Demo mode kicks in automatically when APIFY_API_TOKEN is not set (Apify does
# both discovery and email-finding), or can be forced on via DEMO_MODE=true.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true" or not APIFY_API_TOKEN

HAS_CLAUDE = bool(ANTHROPIC_API_KEY)

CLAUDE_MODEL = "claude-sonnet-5"

# Who counts as a decision maker (see agents/contact_finder.py). A title must
# match no NOT-authority pattern, and then either match an AUTHORITY pattern
# or be a "manager" of a marketing-type function (Marketing Manager, Social
# Media Manager...). Associates, coordinators, specialists, analysts, engineers
# and managers of unrelated functions (Product/Account/Project...) are rejected.
AUTHORITY_TITLE_PATTERNS = [
    r"co-?founder", r"founder", r"owner", r"ceo", r"c[a-z]o", r"chief", r"president",
    r"vp", r"vice president", r"head of", r"director", r"managing director",
    r"general manager", r"managing partner", r"founding partner", r"general partner",
]
NOT_AUTHORITY_PATTERNS = [
    r"assistant", r"intern", r"internship", r"coordinator", r"associate",
    r"specialist", r"analyst", r"representative", r"rep", r"support",
    r"recruiter", r"recruiting", r"developer", r"engineer", r"designer",
    r"student", r"junior", r"chief of staff",
    r"(product|process|account|data|project|service|scrum) owner",
]
# Functions whose "Manager" counts as a decision maker.
MANAGER_FUNCTION_PATTERNS = [
    r"marketing", r"growth", r"brand", r"content", r"social", r"digital",
    r"e-?commerce", r"communications", r"demand", r"advertising",
]
# Among decision makers, prefer whoever owns marketing/growth over other roles.
RELEVANT_TITLE_PATTERNS = [
    r"marketing", r"growth", r"brand", r"content", r"social", r"digital",
    r"e-?commerce", r"communications", r"demand", r"revenue", r"sales",
    r"cmo", r"cgo", r"cro",
]

# Apify contact lookup. Named people with job titles come from the Actor's
# paid "business leads" add-on; on the Free plan it costs $0.10 per person
# returned ($0.005 on paid plans), so keep these small.
APIFY_LEADS_PER_DOMAIN = int(os.getenv("APIFY_LEADS_PER_DOMAIN", "2"))
# Which departments the add-on searches, by company size (see Lead.size_tier).
# Tiny companies: the founder decides, so only the C-suite. Big ones: the
# C-suite is too far from vendor decisions, so only marketing. Unknown size
# (the common case for startups) searches both.
APIFY_DEPARTMENTS_BY_TIER = {
    "micro": ["c_suite"],
    "small": ["c_suite", "marketing"],
    "mid": ["c_suite", "marketing"],
    "large": ["marketing"],
    "unknown": ["c_suite", "marketing"],
}
# Within the same rank, prefer titles matching what a company in this kind of
# industry buys marketing through (tech startups are "b2b").
INDUSTRY_TITLE_PREFS = {
    "b2b": [r"growth", r"demand", r"content", r"product marketing", r"marketing"],
    "consumer": [r"social", r"brand", r"e-?commerce", r"content", r"community"],
    "other": [],
}
# When Apify finds no named decision-maker, derive first@domain from the YC
# founder list. These are flagged "guessed" and are blocked from sending
# until a human confirms them (`main.py confirm-email <id>`).
# A lead needs a VERIFIED point of contact: an address the company publishes itself
# (agents/site_emails.py) or a person confirmed - never a provider's or a guessed one.
REQUIRE_VERIFIED_CONTACT = os.getenv("REQUIRE_VERIFIED_CONTACT", "true").lower() == "true"
VERIFIED_EMAIL_STATUSES = ("published", "linkedin", "confirmed")
# Second check: LinkedIn must show the contact currently holds a decision-making role at the
# company (agents/linkedin.py, ~$0.004 per profile). Fails closed if it cannot be checked.
LINKEDIN_VERIFY = os.getenv("LINKEDIN_VERIFY", "true").lower() == "true"
# apimaestro's actor has no free-plan run cap (harvestapi's stops at 50 runs in total) and costs ~$0.005 per profile.
LINKEDIN_ACTOR = os.getenv("LINKEDIN_ACTOR", "apimaestro/linkedin-profile-detail")
LINKEDIN_MODE = "Profile details no email ($4 per 1k)"      # never the paid email-search mode
# Also accept an email the founder wrote on their own LinkedIn profile (headline, About, role text).
# Never the tool's own email finder - that is pattern guessing.
LINKEDIN_EMAILS = os.getenv("LINKEDIN_EMAILS", "true").lower() == "true"
# Profile reads per discovery run for the email-from-profile pass. The free Apify tier allows only ~20 profile
# reads a day in total, and every lead needs one for its role check, so this pass is off until you upgrade.
LINKEDIN_SCAN_MAX_PROFILES = int(os.getenv("LINKEDIN_SCAN_MAX_PROFILES", "0"))
GUESS_FOUNDER_EMAILS = os.getenv("GUESS_FOUNDER_EMAILS", "false").lower() == "true"
# Hard cap on paid contact lookups per `main.py run` (override with --max-lookups).
# Apify's contact add-on found a decision-maker email for ~1 in 16 YC startups, so it is
# off unless you ask for it. The free route (an address the company publishes for a founder,
# agents/site_emails.py) is tried first either way.
PAID_LOOKUP_FALLBACK = os.getenv("PAID_LOOKUP_FALLBACK", "false").lower() == "true"
MAX_LOOKUPS_PER_RUN = int(os.getenv("MAX_LOOKUPS_PER_RUN", "30"))
# Recent YC batches the discovery agent draws from (open dataset, yc-oss).
YC_BATCHES = ["fall-2026", "summer-2026", "spring-2026", "winter-2026", "fall-2025", "summer-2025", "spring-2025", "winter-2025",
              "fall-2024", "summer-2024", "winter-2024"]
EMAIL_VERIFIER_ACTOR = os.getenv("EMAIL_VERIFIER_ACTOR", "fatihtahta/email-verifier-validator-pro")
APIFY_CONTACT_MAX_CHARGE_USD = float(os.getenv("APIFY_CONTACT_MAX_CHARGE_USD", "0.50"))

SERFIS_PITCH = """
Serfis builds an autonomous AI content pipeline that replaces manual marketing
work with a system of connected digital agents. It draws automatically on a
company's e-commerce product data to generate high-quality, multi-channel
content - eliminating the manual hours spent on content creation. It runs at
a flat cost with infinite scaling, continuously A/B tests content by analyzing
what drives clicks and adapting automatically, and shortens campaign execution
time so brands can move on trends faster and tie content directly to
measurable revenue.
"""

# The kind of company Serfis wants as a lead (enforced by agents/icp.py).
ICP_PROFILE = """
Early-stage tech startups, primarily Y Combinator-backed, whose product has a
clear, demo-able story that works as short-form video. Best fit (P1): consumer
and prosumer AI apps and hardware. Secondary (P2): B2B workflow products with a
visual before/after (insurance, GTM, operations, fintech). Not targets:
infrastructure and developer tools (kept only as research comparables),
established IT-services / outsourcing / agency firms, companies over ~200
people, local businesses, and anything without a decision-maker email.
"""
ICP_MIN_FIT = "Medium"        # lowest tracker fit rating that can become a lead
ICP_MAX_TEAM_SIZE = 200       # above this it isn't an early-stage startup

# What the two email-writing agents (outreach_writer, reply_writer) say. Kept
# separate from SERFIS_PITCH, which scoring and research still use.
EMAIL_OFFER = """
Serfis AI creates short-form video advertisements and social content designed
for TikTok, Instagram, YouTube, Reddit, X, and Pinterest. Social media moves
quickly, and staying on the forefront of emerging trends helps brands remain
relevant, capture attention, and create more opportunities to reach their
target audience. Serfis helps businesses consistently produce innovative
advertisements that fit the style and audience of each platform, rather than relying on the
same content everywhere. The offered next step is a couple of concept ideas
sent over email.
"""

EMAIL_SIGNOFF = "Best,\nAllison\nSerfis AI"

# The approved message. The agents use it as the reference for voice, order
# and the closing ask; the no-LLM fallback templates mirror it.
EMAIL_REFERENCE = """Hi [First Name],

I came across [Company] and really liked [specific thing about their product/brand].

At Serfis AI, we create short-form video advertisements and social content designed for platforms including TikTok, Instagram, YouTube, Reddit, X, and Pinterest.

Social media moves quickly, and staying on the forefront of emerging trends can help brands remain relevant, capture attention, and create more opportunities to reach their target audience. We help businesses consistently produce innovative advertisements that fit the style and audience of each platform rather than relying on the same content everywhere.

I had a few ideas for how [Company] could turn [specific product/service] into engaging social content.

Would you be open to me sending over a couple of concepts?

Best,
Allison
Serfis AI"""

OUTPUT_XLSX = OUTPUT_DIR / "serfis_leads.xlsx"
