"""Step 7: generate a personalized first-touch outreach email.

Required structure:
  - Personalized opening based on company research
  - One relevant business problem or opportunity
  - Brief explanation of how Serfis could help
  - Simple call to action
  - ~75-125 words

This agent only ever produces a DRAFT. Nothing here sends anything - see
README.md "Human approval workflow" and the Phase 2 send-agent stub.
"""
import config
from agents import llm
from models import Lead

SYSTEM_PROMPT = """You write first-touch B2B sales emails for Serfis.

Serfis pitch: {pitch}

Write a single outreach email with this structure:
1. Personalized opening based on the research notes given (reference a real,
   specific detail - not generic flattery)
2. One relevant business problem or opportunity for this specific company
3. Brief explanation of how Serfis could help with that problem
4. A simple, low-friction call to action (e.g. a short call, not a demo/signup)

Constraints: 75-125 words total for the body. Plain, human tone - no hype
words like "revolutionary" or "game-changing". No bullet points. Sign off as
"The Serfis Team".

Return JSON with keys: subject (short, specific, no clickbait), body (the
full email text including greeting and sign-off)."""


class OutreachWriterAgent:
    def write_email(self, lead: Lead) -> Lead:
        if config.HAS_CLAUDE:
            self._write_with_claude(lead)
        else:
            self._write_template(lead)
        return lead

    def _write_with_claude(self, lead: Lead) -> None:
        contact_first_name = (lead.contact_name or "there").split(" ")[0]
        user = (
            f"Company: {lead.company_name}\n"
            f"Contact: {contact_first_name}, {lead.contact_title}\n"
            f"What they sell: {lead.what_they_sell}\n"
            f"Research notes: {lead.research_notes}\n"
            f"Recommended angle: {lead.outreach_angle}\n"
        )
        try:
            data = llm.ask_claude_json(SYSTEM_PROMPT.format(pitch=config.SERFIS_PITCH), user)
            lead.draft_email_subject = data["subject"]
            lead.draft_email_body = data["body"]
            return
        except Exception:
            pass
        self._write_template(lead)

    def _write_template(self, lead: Lead) -> None:
        """No-LLM fallback so the pipeline still produces a usable draft."""
        first_name = (lead.contact_name or "there").split(" ")[0]
        lead.draft_email_subject = f"Quick idea for {lead.company_name}'s content workflow"
        lead.draft_email_body = (
            f"Hi {first_name},\n\n"
            f"{lead.research_notes.strip().split('.')[0]}. As {lead.company_name} grows, "
            f"producing enough high-quality content across channels usually turns into a "
            f"bottleneck for lean marketing teams.\n\n"
            f"Serfis runs an autonomous AI content pipeline that pulls directly from your "
            f"product data to generate and A/B test multi-channel content automatically, "
            f"at a flat cost with no added headcount.\n\n"
            f"Worth a quick 15-minute call to see if it's a fit?\n\n"
            f"The Serfis Team"
        )
