"""Serfis Lead Dashboard - a thin Flask read/write layer over the existing
SQLite leads database. It does not touch the pipeline (orchestrator.py,
agents/*) at all - it only reads and updates rows storage.py already knows
how to manage, and reuses export_excel.export_to_excel() for the Excel
export button.

No outbound email/SMS is sent from anywhere in this file.
"""
import os

from flask import Flask, abort, redirect, render_template, request, send_file, url_for

import config
import storage
from agents import guardrails
from agents.reply_writer import ReplyDraftAgent
from agents.send_agent import looks_like_opt_out
from export_excel import export_to_excel

app = Flask(__name__)

# Human-readable labels for the raw DB values, used in templates.
APPROVAL_LABELS = {
    "pending_review": "Pending Review",
    "approved": "Approved",
    "rejected": "Rejected",
}
LEAD_STATUS_LABELS = {
    "new": "New",
    "contacted": "Contacted",
    "qualified": "Qualified",
    "disqualified": "Disqualified",
    "converted": "Converted",
}
PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "youtube": "YouTube",
    "x": "X",
    "reddit": "Reddit",
}

app.jinja_env.globals.update(
    approval_labels=APPROVAL_LABELS,
    lead_status_labels=LEAD_STATUS_LABELS,
    approval_statuses=storage.APPROVAL_STATUSES,
    lead_statuses=storage.LEAD_STATUSES,
    platform_labels=PLATFORM_LABELS,
    check_summary=guardrails.summary,
)


@app.before_request
def ensure_db():
    storage.init_db()


def _back(lead_id):
    """After a form on the dashboard panel, return to the dashboard with that company still open."""
    if request.form.get("back") == "dashboard":
        return redirect(url_for("dashboard", lead=lead_id) + "#lead-panel")
    return redirect(url_for("lead_detail", lead_id=lead_id))


def _panel_context(lead):
    """Everything the top-of-dashboard panel shows for one company."""
    checks = guardrails.review(lead)
    blocking = guardrails.blocking(lead)
    acknowledged = guardrails.acknowledged(lead)
    sends = storage.get_sends_for_lead(lead.id)
    lookup = storage.get_lookup_row(lead.website)
    suppressed = storage.is_suppressed(lead.contact_email) if lead.has_email() else False
    cooldown = guardrails.company_cooldown(lead) if lead.has_email() else None
    verified = lead.has_email() and lead.email_status in config.VERIFIED_EMAIL_STATUSES
    has_draft = bool(lead.draft_email_subject and lead.draft_email_body)

    # Readiness: the four things that must be true before an approval is safe.
    readiness = [
        {"label": "Verified contact", "ok": verified,
         "detail": lead.contact_check or ("no verified email" if not verified else "")},
        {"label": "Draft email checked", "ok": has_draft and (not checks["draft"] or "draft" in acknowledged),
         "detail": (("; ".join(checks["draft"]) + (" (you approved anyway)" if "draft" in acknowledged else "")) if checks["draft"] else ("clear" if has_draft else "no draft"))},
        {"label": "Location checked", "ok": (not checks["region"]) or "region" in acknowledged,
         "detail": (("; ".join(checks["region"]) + (" (you approved anyway)" if "region" in acknowledged else "")) if checks["region"] else (lead.location or "clear"))},
        {"label": "Safe to contact", "ok": not suppressed and not cooldown,
         "detail": "on the do-not-contact list" if suppressed else (cooldown or "not suppressed, not emailed in 90 days")},
    ]
    sent = bool(sends) or lead.lead_status in ("contacted", "qualified", "converted")
    approved, rejected = lead.approval_status == "approved", lead.approval_status == "rejected"
    steps = [
        {"label": "Company found", "state": "done", "note": (lead.created_at or "")[:10]},
        {"label": "Contact verified", "state": "done" if verified else "fail", "note": lead.email_status or "not verified"},
        {"label": "Draft ready", "state": "done" if has_draft else "fail", "note": ("none" if not has_draft else ("needs review" if (checks["draft"] and "draft" not in acknowledged) else "checked"))},
        {"label": "YOUR APPROVAL", "state": "done" if approved else ("rejected" if rejected else "current"),
         "note": (lead.decided_at or "")[:16].replace("T", " ") if lead.decided_at else "waiting on you", "manual": True},
        {"label": "Email sent", "state": "done" if sent else ("next" if approved else "todo"),
         "note": (sends[-1]["sent_at"][:16].replace("T", " ") if sends else ("run send-approved" if approved else ""))},
    ]
    return dict(lead=lead, analytics=storage.get_platform_analytics(lead.id), messages=storage.get_messages(lead.id),
                checks=checks, blocking=blocking, acknowledged=acknowledged, sending_state=guardrails.pause_reason(),
                sends=sends, lookup=lookup, suppressed=suppressed, cooldown=cooldown, readiness=readiness,
                ready_count=sum(1 for r in readiness if r["ok"]), steps=steps,
                all_fields=list(lead.as_dict().items()),
                risk_events=storage.get_risk_events_for(lead.contact_email) if lead.has_email() else [])


def _approval_funnel():
    """Counts for the approval-queue bar: who is waiting on you, what you approved, what went out."""
    leads = storage.get_all_leads()
    sent_ids = {r["lead_id"] for r in storage.recent_sends(3650)}
    waiting = approved = sent = rejected = 0
    for l in leads:
        if l.approval_status == "rejected":
            rejected += 1
        elif l.approval_status == "pending_review":
            waiting += 1
        elif l.id in sent_ids or l.lead_status in ("contacted", "qualified", "converted"):
            sent += 1
        else:
            approved += 1
    total = len(leads) or 1
    segs = [("waiting", "Waiting for your approval", waiting), ("approved", "Approved, not sent yet", approved),
            ("sent", "Sent", sent), ("rejected", "Rejected", rejected)]
    return {"total": len(leads), "waiting": waiting,
            "segments": [{"key": k, "label": lbl, "n": n, "pct": round(100 * n / total)} for k, lbl, n in segs]}


@app.route("/panel/<int:lead_id>")
def lead_panel(lead_id):
    lead = storage.get_lead(lead_id)
    if lead is None:
        abort(404)
    return render_template("_lead_panel.html", **_panel_context(lead))


@app.route("/")
def dashboard():
    search = request.args.get("q", "").strip()
    icp_score = request.args.get("icp_score", "").strip()
    lead_status = request.args.get("lead_status", "").strip()
    approval_status = request.args.get("approval_status", "").strip()
    industry = request.args.get("industry", "").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    leads = storage.query_leads(
        search=search,
        icp_score=int(icp_score) if icp_score.isdigit() else None,
        lead_status=lead_status,
        approval_status=approval_status,
        industry=industry,
        sort_by="icp_fit_score",
        sort_dir=sort_dir,
    )

    selected = None
    lead_arg = request.args.get("lead", "").strip()
    if lead_arg.isdigit():
        picked = storage.get_lead(int(lead_arg))
        if picked is not None:
            selected = _panel_context(picked)
    return render_template(
        "dashboard.html",
        leads=leads,
        selected=selected,
        selected_id=(selected["lead"].id if selected else None),
        funnel=_approval_funnel(),
        **{k: v for k, v in (selected or {}).items() if k != "sending_state"},
        stats=storage.get_summary_stats(),
        sending_state=guardrails.pause_reason(),
        industries=storage.get_distinct_industries(),
        filters={
            "q": search,
            "icp_score": icp_score,
            "lead_status": lead_status,
            "approval_status": approval_status,
            "industry": industry,
            "sort_dir": sort_dir,
        },
    )


@app.route("/lead/<int:lead_id>")
def lead_detail(lead_id):
    lead = storage.get_lead(lead_id)
    if lead is None:
        abort(404)
    analytics = storage.get_platform_analytics(lead_id)
    messages = storage.get_messages(lead_id)
    return render_template("lead_detail.html", lead=lead, analytics=analytics, messages=messages,
                           checks=guardrails.review(lead), blocking=guardrails.blocking(lead),
                           acknowledged=guardrails.acknowledged(lead), sending_state=guardrails.pause_reason())


@app.route("/lead/<int:lead_id>/approve", methods=["POST"])
def approve_lead(lead_id):
    lead = storage.get_lead(lead_id)
    if lead is None:
        abort(404)
    flagged = guardrails.blocking(lead)
    if flagged:
        # A flagged lead is only approved if a person explicitly chose "Approve anyway".
        if request.form.get("override") != "1":
            return _back(lead_id)
        storage.set_overrides(lead_id, ",".join(sorted(guardrails.acknowledged(lead) | {c for c, _ in flagged})))
    storage.set_approval_status(lead_id, "approved")
    return _back(lead_id)


@app.route("/lead/<int:lead_id>/reject", methods=["POST"])
def reject_lead(lead_id):
    if storage.get_lead(lead_id) is None:
        abort(404)
    storage.set_approval_status(lead_id, "rejected")
    return _back(lead_id)


@app.route("/lead/<int:lead_id>/status", methods=["POST"])
def update_lead_status(lead_id):
    if storage.get_lead(lead_id) is None:
        abort(404)
    new_status = request.form.get("lead_status", "")
    if new_status not in storage.LEAD_STATUSES:
        abort(400)
    storage.set_lead_status(lead_id, new_status)
    return _back(lead_id)


@app.route("/lead/<int:lead_id>/log-reply", methods=["POST"])
def log_reply(lead_id):
    """A human pastes in a reply a prospect actually sent (there's no live
    inbox connection - this is a manual log step). That triggers
    ReplyDraftAgent to draft a suggested response, saved as pending_review.
    Nothing here sends anything."""
    lead = storage.get_lead(lead_id)
    if lead is None:
        abort(404)

    inbound_subject = request.form.get("inbound_subject", "").strip()
    inbound_body = request.form.get("inbound_body", "").strip()
    if not inbound_body:
        abort(400)

    storage.log_inbound_message(lead_id, inbound_subject, inbound_body)

    # A request to stop emailing is honored, not answered with another pitch.
    if looks_like_opt_out(f"{inbound_subject} {inbound_body}"):
        storage.add_suppression(lead.contact_email, "asked to unsubscribe")
        return _back(lead_id)

    subject, body = ReplyDraftAgent().draft_reply(
        lead,
        original_subject=lead.draft_email_subject,
        original_body=lead.draft_email_body,
        inbound_subject=inbound_subject,
        inbound_body=inbound_body,
    )
    storage.save_reply_draft(lead_id, subject, body)

    return _back(lead_id)


@app.route("/message/<int:message_id>/approve", methods=["POST"])
def approve_message(message_id):
    message = storage.get_message(message_id)
    if message is None:
        abort(404)
    storage.set_message_approval(message_id, "approved")
    return _back(message["lead_id"])


@app.route("/message/<int:message_id>/reject", methods=["POST"])
def reject_message(message_id):
    message = storage.get_message(message_id)
    if message is None:
        abort(404)
    storage.set_message_approval(message_id, "rejected")
    return _back(message["lead_id"])


@app.route("/export")
def export_leads():
    path = export_to_excel()
    return send_file(path, as_attachment=True, download_name="serfis_leads.xlsx")


if __name__ == "__main__":
    storage.init_db()
    # Default port 5050, not 5000 - macOS's AirPlay Receiver (ControlCenter)
    # squats on 5000 by default and the OS returns a confusing connection
    # refusal instead of "port in use". Override with PORT=xxxx if needed.
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=True, port=port)
