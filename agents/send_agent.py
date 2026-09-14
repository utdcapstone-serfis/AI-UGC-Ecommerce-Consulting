"""PHASE 2 - NOT WIRED UP. Placeholder for automated sending.

The current pipeline (orchestrator.py / main.py) never imports this module.
Every lead stops at approval_status='pending_review' in the database and
Excel export - a human must review the draft and flip the status to
'approved' before anything could be sent.

When you're ready to add real sending:
1. Implement `send(lead)` below using an ESP (SendGrid, Postmark, Gmail API, etc.)
2. Only ever call it for leads where approval_status == 'approved'
3. After a successful send, call storage.set_lead_status(lead.id, 'contacted')
   (approval_status stays 'approved' - lead_status tracks that outreach went out)
4. Add a CLI flag (e.g. `--send-approved`) to main.py, and/or a "Send" action
   in the dashboard, that is off by default
"""
from models import Lead


def send(lead: Lead) -> None:
    if lead.approval_status != "approved":
        raise RuntimeError(
            f"Refusing to send lead {lead.id} ({lead.company_name}): "
            f"approval_status is '{lead.approval_status}', not 'approved'."
        )
    raise NotImplementedError(
        "Sending is intentionally not implemented yet - wire up an ESP here "
        "when you're ready to move past human-approval mode."
    )
