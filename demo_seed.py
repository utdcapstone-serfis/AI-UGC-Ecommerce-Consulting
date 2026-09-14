"""Seeds exactly ONE clearly-fictional sample lead so the dashboard can show
what a fully worked lead - through conversion and into content performance
analytics - looks like, without claiming any real company's real numbers.

This is intentionally separate from orchestrator.py: nothing here is part of
the discovery -> enrichment -> ... -> outreach pipeline. It's demo fixture
data only, and it's the only place in the codebase that writes to
platform_analytics with made-up numbers.

The sample company uses a .example domain (reserved by RFC 2606 for
documentation - it will never resolve to a real site), is named "Serfis
Sample" so its nature is obvious at a glance, and is tagged
source='demo_sample' in the DB. seed_demo_lead() always clears out any prior
demo_sample rows first, so re-running it (or renaming the sample here) never
leaves more than one sample lead behind.

Run with: python main.py seed-demo
"""
import storage
from models import Lead

SAMPLE_COMPANY = "Serfis Sample"
SAMPLE_WEBSITE = "https://serfissample.example"

# views/likes/shares/comments are illustrative only - not pulled from any
# real platform API. "Shares" maps to Retweets on X and is left at 0 for
# Reddit (awards aren't a comparable concept); "views" on Reddit is an
# estimate since Reddit doesn't expose post view counts the way video
# platforms do.
SAMPLE_ANALYTICS = {
    "facebook": {"views": 18400, "likes": 1240, "shares": 310, "comments": 96},
    "instagram": {"views": 42500, "likes": 3870, "shares": 540, "comments": 215},
    "youtube": {"views": 9800, "likes": 612, "shares": 88, "comments": 143},
    "x": {"views": 7600, "likes": 340, "shares": 120, "comments": 58},
    "reddit": {"views": 5200, "likes": 890, "shares": 0, "comments": 134},
}


def seed_demo_lead() -> Lead:
    storage.delete_leads_by_source("demo_sample")

    lead = Lead(
        company_name=SAMPLE_COMPANY,
        website=SAMPLE_WEBSITE,
        industry="E-commerce / DTC Apparel (SaaS-enabled)",
        company_size="11-50",
        location="Austin, TX",
        what_they_sell=(
            "Direct-to-consumer outdoor apparel and gear, sold through their own "
            "Shopify storefront with a small in-house marketing team."
        ),
        funding_notes="Sample data - illustrative $6M Series A, not a real funding event.",
        icp_fit_score=9,
        why_it_fits=(
            "Fast-growing DTC e-commerce brand with a lean marketing team and high "
            "content velocity needs across channels - exactly the profile Serfis's "
            "content pipeline is built for. (Sample reasoning for demo purposes.)"
        ),
        contact_name="Jordan Rivera (Sample Contact)",
        contact_title="Head of Growth",
        contact_email="jordan@serfissample.example",
        contact_profile_url="https://www.linkedin.com/in/sample-profile-not-real",
        research_notes=(
            "Sample research notes: recently expanded into two new product lines; "
            "current content output is mostly manual and inconsistent across channels; "
            "marketing team of 3 supporting a fast-growing catalog."
        ),
        research_sources="Sample data - not drawn from a live scrape or search",
        outreach_angle=(
            "Position Serfis as the way to keep content output matching their catalog "
            "growth without adding headcount, with built-in A/B testing across channels."
        ),
        draft_email_subject="Quick idea for your content workflow",
        draft_email_body=(
            "Hi Jordan,\n\n"
            "Noticed your catalog has grown fast this year, which usually means "
            "content production becomes the bottleneck for a lean team.\n\n"
            "At Serfis, we help teams like yours keep content flowing across every "
            "channel without adding headcount - and constantly test what's actually "
            "working, so you're never guessing.\n\n"
            "Feel free to reply if you have any questions - happy to help.\n\n"
            "The Serfis Team"
        ),
        approval_status="approved",
        lead_status="converted",
        source="demo_sample",
    )
    lead = storage.save_lead(lead)

    for platform, metrics in SAMPLE_ANALYTICS.items():
        storage.upsert_platform_analytics(lead.id, platform, **metrics)

    return lead


if __name__ == "__main__":
    storage.init_db()
    lead = seed_demo_lead()
    print(f"Seeded sample converted lead: {lead.company_name} (id={lead.id})")
