"""Serfis Lead Dashboard - a thin Flask read/write layer over the existing
SQLite leads database. It does not touch the pipeline (orchestrator.py,
agents/*) at all - it only reads and updates rows storage.py already knows
how to manage, and reuses export_excel.export_to_excel() for the Excel
export button.

No outbound email/SMS is sent from anywhere in this file.
"""
import os

from flask import Flask, abort, redirect, render_template, request, send_file, url_for

import storage
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
)


@app.before_request
def ensure_db():
    storage.init_db()


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

    return render_template(
        "dashboard.html",
        leads=leads,
        stats=storage.get_summary_stats(),
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
    return render_template("lead_detail.html", lead=lead, analytics=analytics, messages=messages)


@app.route("/lead/<int:lead_id>/approve", methods=["POST"])
def approve_lead(lead_id):
    if storage.get_lead(lead_id) is None:
        abort(404)
    storage.set_approval_status(lead_id, "approved")
    return redirect(url_for("lead_detail", lead_id=lead_id))


@app.route("/lead/<int:lead_id>/reject", methods=["POST"])
def reject_lead(lead_id):
    if storage.get_lead(lead_id) is None:
        abort(404)
    storage.set_approval_status(lead_id, "rejected")
    return redirect(url_for("lead_detail", lead_id=lead_id))


@app.route("/lead/<int:lead_id>/status", methods=["POST"])
def update_lead_status(lead_id):
    if storage.get_lead(lead_id) is None:
        abort(404)
    new_status = request.form.get("lead_status", "")
    if new_status not in storage.LEAD_STATUSES:
        abort(400)
    storage.set_lead_status(lead_id, new_status)
    return redirect(url_for("lead_detail", lead_id=lead_id))


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
        return redirect(url_for("lead_detail", lead_id=lead_id))

    subject, body = ReplyDraftAgent().draft_reply(
        lead,
        original_subject=lead.draft_email_subject,
        original_body=lead.draft_email_body,
        inbound_subject=inbound_subject,
        inbound_body=inbound_body,
    )
    storage.save_reply_draft(lead_id, subject, body)

    return redirect(url_for("lead_detail", lead_id=lead_id))


@app.route("/message/<int:message_id>/approve", methods=["POST"])
def approve_message(message_id):
    message = storage.get_message(message_id)
    if message is None:
        abort(404)
    storage.set_message_approval(message_id, "approved")
    return redirect(url_for("lead_detail", lead_id=message["lead_id"]))


@app.route("/message/<int:message_id>/reject", methods=["POST"])
def reject_message(message_id):
    message = storage.get_message(message_id)
    if message is None:
        abort(404)
    storage.set_message_approval(message_id, "rejected")
    return redirect(url_for("lead_detail", lead_id=message["lead_id"]))


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
