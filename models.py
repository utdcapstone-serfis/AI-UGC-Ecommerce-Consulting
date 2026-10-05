"""Data structures shared across every agent in the pipeline."""
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Lead:
    company_name: str
    website: str = ""
    industry: str = ""
    company_size: str = ""
    location: str = ""
    what_they_sell: str = ""
    funding_notes: str = ""

    icp_fit_score: Optional[int] = None
    why_it_fits: str = ""

    contact_name: str = ""
    contact_title: str = ""
    contact_email: str = ""
    contact_profile_url: str = ""

    research_notes: str = ""
    research_sources: str = ""
    outreach_angle: str = ""
    draft_email_subject: str = ""
    draft_email_body: str = ""

    approval_status: str = "pending_review"  # pending_review | approved | rejected
    lead_status: str = "new"  # new | contacted | qualified | disqualified
    source: str = ""

    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return asdict(self)

    def size_tier(self) -> str:
        """micro (1-10), small (11-50), mid (51-500), large (500+) or unknown,
        from the free-text company_size ("11-50", "500+", "~120 employees")."""
        text = self.company_size or ""
        nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)]
        if not nums:
            return "unknown"
        n = max(nums) + (1 if "+" in text else 0)
        return "micro" if n <= 10 else "small" if n <= 50 else "mid" if n <= 500 else "large"

    def has_email(self) -> bool:
        """True only for a real address - blank or NEEDS_ENRICHMENT is not one."""
        email = (self.contact_email or "").strip()
        return "@" in email and email.upper() != "NEEDS_ENRICHMENT"

    def first_name(self) -> str:
        """Greeting name; "there" when the contact is unknown or unenriched."""
        name = (self.contact_name or "").strip()
        if not name or name.upper() == "NEEDS_ENRICHMENT":
            return "there"
        return name.split(" ")[0]

    def product_phrase(self) -> str:
        """Short noun phrase for what they sell, for use mid-sentence.

        "Direct-to-consumer outdoor apparel and gear, sold through ..." becomes
        "direct-to-consumer outdoor apparel and gear". Returns "" when the text
        is scraped page chrome or just the company's own name, so callers fall
        back to generic wording instead of pasting junk into an email.
        """
        text = (self.what_they_sell or "").strip()
        text = re.sub(r"^(sells|what they sell)\s*:\s*", "", text, flags=re.I)
        text = re.split(r"[,;:|\u2013\u2014]| - | sold | with | that | which |\. ",
                        text, maxsplit=1)[0].strip().rstrip(".")
        low = text.lower()
        junk = ("skip to", "cookie", "install", "sign in", "log in", "get started",
                "learn more", "menu", "\u00a9", "\u2192")
        if (not text or len(text) > 60 or any(j in low for j in junk)
                or (self.company_name or "").lower() in low):
            return ""
        if sum(w[:1].isupper() for w in text.split()) >= 3:  # Title Case heading
            return text.lower()
        return text[:1].lower() + text[1:]

    def print_block(self) -> str:
        """Render the lead in the exact output format requested for review."""
        return (
            f"Company: {self.company_name}\n"
            f"Website: {self.website}\n"
            f"Industry: {self.industry}\n"
            f"Company Size: {self.company_size}\n"
            f"ICP Fit Score (1-10): {self.icp_fit_score}\n"
            f"Why It Fits: {self.why_it_fits}\n"
            f"Contact Name: {self.contact_name}\n"
            f"Contact Title: {self.contact_title}\n"
            f"Contact Email: {self.contact_email}\n"
            f"Contact/Profile URL: {self.contact_profile_url}\n"
            f"Research Notes: {self.research_notes}\n"
            f"Research Sources: {self.research_sources}\n"
            f"Funding Notes: {self.funding_notes}\n"
            f"Recommended Outreach Angle: {self.outreach_angle}\n"
            f"Draft Email:\nSubject: {self.draft_email_subject}\n{self.draft_email_body}\n"
        )
