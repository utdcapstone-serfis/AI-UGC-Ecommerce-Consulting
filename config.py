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

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Demo mode kicks in automatically when NEITHER discovery/contact provider
# key is set, or can be forced on via DEMO_MODE=true. Having just one of the
# two (e.g. only Hunter) is enough to leave demo mode - each agent checks its
# own specific key before calling that provider and falls back gracefully
# (see agents/discovery.py and agents/contact_finder.py) if only one is set.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true" or not (
    APOLLO_API_KEY or HUNTER_API_KEY
)

HAS_CLAUDE = bool(ANTHROPIC_API_KEY)

CLAUDE_MODEL = "claude-sonnet-5"

# Preferred point-of-contact job titles, in priority order.
PREFERRED_TITLES = [
    "founder",
    "co-founder",
    "ceo",
    "chief executive",
    "head of growth",
    "growth lead",
    "vp growth",
    "head of marketing",
    "cmo",
    "vp marketing",
    "marketing director",
    "e-commerce",
    "ecommerce",
    "head of customer success",
    "customer success lead",
    "vp sales",
    "head of revenue",
    "chief revenue officer",
    "vp revenue",
    "sales director",
]

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

OUTPUT_XLSX = OUTPUT_DIR / "serfis_leads.xlsx"
