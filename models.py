"""Data structures shared across every agent in the pipeline."""
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
