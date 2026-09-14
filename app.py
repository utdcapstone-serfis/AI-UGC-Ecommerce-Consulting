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
    return render_template("lead_detail.html", lead=lead, analytics=analytics)


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
