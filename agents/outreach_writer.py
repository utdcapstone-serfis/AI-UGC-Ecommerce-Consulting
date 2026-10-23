"""Step 7: generate a personalized first-touch outreach email.

Required structure:
  - Personalized opening based on company research
  - One relevant business problem or opportunity
  - Brief explanation of how Serfis could help
  - Simple call to action
  - ~110-170 words

This agent only ever produces a DRAFT. Nothing here sends anything - see
README.md "Human approval workflow" and the Phase 2 send-agent stub.
"""
import config
from agents import llm
from models import Lead

SYSTEM_PROMPT = """You write first-touch B2B outreach emails for Serfis AI.

What Serfis offers: {offer}

This is the approved message. Follow its structure, voice and closing ask,
but replace every [bracket] with real, specific details for this company:
---
{reference}
---

Rules:
- Open with a genuine, specific detail from the research notes about their
  product or brand - not generic flattery.
- Keep the same order: what Serfis does and the platforms, why innovative,
  per-platform advertisements matter, the idea for turning their specific product
  into social content, then the closing question about sending a couple of
  concepts over email.
- Never use the phrase "fresh creative" (it reads oddly). Say "innovative advertisements".
- Do NOT ask for a phone call, meeting or demo - this is email only.
- "Serfis AI" is the company name and is fine to use. Never describe the
  system as "an autonomous AI" or "an AI pipeline" or explain how it works.
- Plain text only (no markdown, no bold, no bullets). Human tone, no hype
  words. 110-170 words.
- Sign off exactly as:
{signoff}

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
        contact_first_name = lead.first_name()
        user = (
            f"Company: {lead.company_name}\n"
            f"Contact: {contact_first_name}, {lead.contact_title}\n"
            f"What they sell: {lead.what_they_sell}\n"
            f"Research notes: {lead.research_notes}\n"
            f"Recommended angle: {lead.outreach_angle}\n"
        )
        try:
            data = llm.ask_claude_json(SYSTEM_PROMPT.format(
                offer=config.EMAIL_OFFER.strip(),
                reference=config.EMAIL_REFERENCE,
                signoff=config.EMAIL_SIGNOFF,
            ), user)
            lead.draft_email_subject = data["subject"]
            lead.draft_email_body = data["body"]
            return
        except Exception:
            pass
        self._write_template(lead)

    def _write_template(self, lead: Lead) -> None:
        """No-LLM fallback so the pipeline still produces a usable draft."""
        first_name = lead.first_name()
        what = lead.product_phrase()
        liked = (
            f"what you're doing with {what}"
            if what else "what you're building"
        )
        ideas = (
            f"turn {what} into engaging social content"
            if what else "turn what you do into engaging social content"
        )
        lead.draft_email_subject = f"Short-form video ideas for {lead.company_name}"
        lead.draft_email_body = (
            f"Hi {first_name},\n\n"
            f"I came across {lead.company_name} and really liked {liked}.\n\n"
            f"At Serfis AI, we create short-form video advertisements and social content "
            f"designed for platforms including TikTok, Instagram, YouTube, Reddit, X, and "
            f"Pinterest.\n\n"
            f"Social media moves quickly, and staying on the forefront of emerging trends "
            f"can help brands remain relevant, capture attention, and create more "
            f"opportunities to reach their target audience. We help businesses consistently "
            f"produce innovative advertisements that fit the style and audience of each platform "
            f"rather than relying on the same content everywhere.\n\n"
            f"I had a few ideas for how {lead.company_name} could {ideas}.\n\n"
            f"Would you be open to me sending over a couple of concepts?\n\n"
            f"{config.EMAIL_SIGNOFF}"
        )
