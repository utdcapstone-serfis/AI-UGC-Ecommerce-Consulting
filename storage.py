"""SQLite persistence for leads. One table, simple CRUD, no ORM needed at MVP scale."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

import config
from models import Lead

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    website TEXT,
    industry TEXT,
    company_size TEXT,
    location TEXT,
    what_they_sell TEXT,
    funding_notes TEXT,
    icp_fit_score INTEGER,
    why_it_fits TEXT,
    contact_name TEXT,
    contact_title TEXT,
    contact_email TEXT,
    contact_profile_url TEXT,
    research_notes TEXT,
    research_sources TEXT,
    outreach_angle TEXT,
    draft_email_subject TEXT,
    draft_email_body TEXT,
    approval_status TEXT DEFAULT 'pending_review',
    lead_status TEXT DEFAULT 'new',
    source TEXT,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(company_name, website)
);
"""

# Content performance metrics for a converted lead, one row per platform.
# Populated manually today (see demo_seed.py) - a future ContentAnalyticsAgent
# could fill this from each platform's real API once content is actually
# being published for converted customers.
PLATFORM_ANALYTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    updated_at TEXT,
    UNIQUE(lead_id, platform),
    FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE
);
"""

PLATFORMS = ["facebook", "instagram", "youtube", "x", "reddit"]

# Conversation thread for a lead, beyond the first-touch email already stored
# on the leads row itself. 'inbound' rows are logged manually by a human
# (pasting in what a prospect actually wrote - there is no live inbox
# connection yet, see agents/reply_writer.py). 'outbound' rows are draft
# replies from ReplyDraftAgent and follow the exact same pending_review /
# approved / rejected lifecycle as the first-touch email - nothing here is
# ever sent automatically.
MESSAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    approval_status TEXT,
    created_at TEXT,
    FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE
);
"""

MESSAGE_DIRECTIONS = ["inbound", "outbound"]

# Columns added after the table originally shipped. Kept as (name, sql_type,
# default) so init_db() can ALTER an existing leads.db in place without
# losing data - this is what lets the dashboard sit on top of a DB the
# pipeline already populated in an earlier run.
_MIGRATIONS = [
    ("research_sources", "TEXT", "''"),
    ("lead_status", "TEXT", "'new'"),
]

_FIELDS = [
    "company_name", "website", "industry", "company_size", "location",
    "what_they_sell", "funding_notes", "icp_fit_score", "why_it_fits",
    "contact_name", "contact_title", "contact_email", "contact_profile_url",
    "research_notes", "research_sources", "outreach_angle",
    "draft_email_subject", "draft_email_body",
    "approval_status", "lead_status", "source", "created_at", "updated_at",
]

SUPPRESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS suppressions (
    email TEXT PRIMARY KEY,
    reason TEXT,
    added_at TEXT NOT NULL
)
"""

SENT_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    to_email TEXT NOT NULL,
    subject TEXT,
    sent_at TEXT NOT NULL,
    sent_on TEXT NOT NULL
)
"""

APPROVAL_STATUSES = ["pending_review", "approved", "rejected"]
LEAD_STATUSES = ["new", "contacted", "qualified", "disqualified", "converted"]


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(SCHEMA)
        conn.execute(PLATFORM_ANALYTICS_SCHEMA)
        conn.execute(MESSAGES_SCHEMA)
        conn.execute(SUPPRESSIONS_SCHEMA)
        conn.execute(SENT_LOG_SCHEMA)
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(leads)")}
        for col_name, col_type, default in _MIGRATIONS:
            if col_name not in existing_cols:
                conn.execute(
                    f"ALTER TABLE leads ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                )


def delete_leads_by_source(source: str) -> None:
    """Removes every lead (and its analytics) tagged with the given `source`
    value - used by demo_seed.py so re-seeding never leaves duplicates behind
    if the sample company's name/details change."""
    with get_conn() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM leads WHERE source=?", (source,))]
        for lead_id in ids:
            conn.execute("DELETE FROM platform_analytics WHERE lead_id=?", (lead_id,))
        conn.execute("DELETE FROM leads WHERE source=?", (source,))


def reset_all_leads() -> None:
    """Wipe every lead and its analytics. Used to return the dashboard to an
    empty, pre-pipeline-run state - e.g. before a real demo/handoff where
    stale test data from development shouldn't be shown as real leads."""
    with get_conn() as conn:
        conn.execute("DELETE FROM leads")
        conn.execute("DELETE FROM platform_analytics")
        conn.execute("DELETE FROM messages")


def save_lead(lead: Lead) -> Lead:
    """Insert a new lead, or update it in place if (company_name, website) already exists."""
    lead.updated_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cols = ", ".join(_FIELDS)
        placeholders = ", ".join(f":{f}" for f in _FIELDS)
        updates = ", ".join(f"{f}=excluded.{f}" for f in _FIELDS if f not in ("created_at",))
        sql = (
            f"INSERT INTO leads ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(company_name, website) DO UPDATE SET {updates}"
        )
        conn.execute(sql, lead.as_dict())
        row = conn.execute(
            "SELECT id FROM leads WHERE company_name=? AND website=?",
            (lead.company_name, lead.website),
        ).fetchone()
        lead.id = row["id"]
    return lead


def get_all_leads() -> list[Lead]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY icp_fit_score DESC, id DESC").fetchall()
    return [_row_to_lead(r) for r in rows]


def get_lead(lead_id: int) -> Optional[Lead]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    return _row_to_lead(row) if row else None


def get_leads_by_status(status: str) -> list[Lead]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE approval_status=? ORDER BY icp_fit_score DESC", (status,)
        ).fetchall()
    return [_row_to_lead(r) for r in rows]


def query_leads(
    search: str = "",
    icp_score: Optional[int] = None,
    lead_status: str = "",
    approval_status: str = "",
    industry: str = "",
    sort_by: str = "icp_fit_score",
    sort_dir: str = "desc",
) -> list[Lead]:
    """Server-side search/filter/sort used by the dashboard table."""
    clauses = []
    params: list = []

    if search:
        clauses.append("company_name LIKE ?")
        params.append(f"%{search}%")
    if icp_score is not None:
        clauses.append("icp_fit_score >= ?")
        params.append(icp_score)
    if lead_status:
        clauses.append("lead_status = ?")
        params.append(lead_status)
    if approval_status:
        clauses.append("approval_status = ?")
        params.append(approval_status)
    if industry:
        clauses.append("industry = ?")
        params.append(industry)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    sort_col = sort_by if sort_by in {"icp_fit_score", "company_name", "created_at"} else "icp_fit_score"
    sort_dir_sql = "ASC" if sort_dir.lower() == "asc" else "DESC"

    sql = (
        f"SELECT * FROM leads {where_sql} "
        f"ORDER BY {sort_col} {sort_dir_sql} NULLS LAST, id DESC"
    )
    with get_conn() as conn:
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            # Older SQLite builds (<3.30) don't support NULLS LAST.
            sql = f"SELECT * FROM leads {where_sql} ORDER BY {sort_col} {sort_dir_sql}, id DESC"
            rows = conn.execute(sql, params).fetchall()
    return [_row_to_lead(r) for r in rows]


def get_distinct_industries() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != '' "
            "ORDER BY industry"
        ).fetchall()
    return [r["industry"] for r in rows]


def get_summary_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
        qualified = conn.execute(
            "SELECT COUNT(*) c FROM leads WHERE icp_fit_score >= 7"
        ).fetchone()["c"]
        pending = conn.execute(
            "SELECT COUNT(*) c FROM leads WHERE approval_status='pending_review'"
        ).fetchone()["c"]
        approved = conn.execute(
            "SELECT COUNT(*) c FROM leads WHERE approval_status='approved'"
        ).fetchone()["c"]
        rejected = conn.execute(
            "SELECT COUNT(*) c FROM leads WHERE approval_status='rejected'"
        ).fetchone()["c"]
        sample_count = conn.execute(
            "SELECT COUNT(*) c FROM leads WHERE source='demo_sample'"
        ).fetchone()["c"]
    return {
        "total": total,
        "qualified": qualified,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "sample_count": sample_count,
    }


def set_approval_status(lead_id: int, status: str) -> None:
    assert status in APPROVAL_STATUSES, f"invalid approval_status: {status}"
    with get_conn() as conn:
        conn.execute(
            "UPDATE leads SET approval_status=?, updated_at=? WHERE id=?",
            (status, datetime.now(timezone.utc).isoformat(), lead_id),
        )


def set_lead_status(lead_id: int, status: str) -> None:
    assert status in LEAD_STATUSES, f"invalid lead_status: {status}"
    with get_conn() as conn:
        conn.execute(
            "UPDATE leads SET lead_status=?, updated_at=? WHERE id=?",
            (status, datetime.now(timezone.utc).isoformat(), lead_id),
        )


def upsert_platform_analytics(
    lead_id: int, platform: str, views: int = 0, likes: int = 0, shares: int = 0, comments: int = 0
) -> None:
    assert platform in PLATFORMS, f"invalid platform: {platform}"
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO platform_analytics (lead_id, platform, views, likes, shares, comments, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id, platform) DO UPDATE SET
                views=excluded.views, likes=excluded.likes, shares=excluded.shares,
                comments=excluded.comments, updated_at=excluded.updated_at
            """,
            (lead_id, platform, views, likes, shares, comments, datetime.now(timezone.utc).isoformat()),
        )


def get_platform_analytics(lead_id: int) -> list[dict]:
    """Returns one row per platform that has data, in PLATFORMS order."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM platform_analytics WHERE lead_id=?", (lead_id,)
        ).fetchall()
    by_platform = {r["platform"]: dict(r) for r in rows}
    return [by_platform[p] for p in PLATFORMS if p in by_platform]


def log_inbound_message(lead_id: int, subject: str, body: str) -> int:
    """Records a message a prospect actually sent (pasted in by a human -
    there's no live inbox connection). Returns the new message id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (lead_id, direction, subject, body, approval_status, created_at) "
            "VALUES (?, 'inbound', ?, ?, NULL, ?)",
            (lead_id, subject, body, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def save_reply_draft(lead_id: int, subject: str, body: str) -> int:
    """Stores a drafted reply awaiting human approval. Never sent automatically."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (lead_id, direction, subject, body, approval_status, created_at) "
            "VALUES (?, 'outbound', ?, ?, 'pending_review', ?)",
            (lead_id, subject, body, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def get_messages(lead_id: int) -> list[dict]:
    """Full conversation thread for a lead, oldest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE lead_id=? ORDER BY created_at ASC, id ASC", (lead_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_message(message_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    return dict(row) if row else None


def set_message_approval(message_id: int, status: str) -> None:
    assert status in APPROVAL_STATUSES, f"invalid approval_status: {status}"
    with get_conn() as conn:
        conn.execute("UPDATE messages SET approval_status=? WHERE id=?", (status, message_id))


def _row_to_lead(row: sqlite3.Row) -> Lead:
    data = {k: row[k] for k in row.keys() if k != "id"}
    lead = Lead(**data)
    lead.id = row["id"]
    return lead


# ---- do-not-contact list and sent log (used by agents/send_agent.py) ----

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def add_suppression(email: str, reason: str = "") -> None:
    """Never email this address again. Safe to call repeatedly."""
    email = normalize_email(email)
    if "@" not in email:
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO suppressions (email, reason, added_at) VALUES (?, ?, ?)",
            (email, reason, datetime.now(timezone.utc).isoformat()),
        )


def is_suppressed(email: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM suppressions WHERE email=?", (normalize_email(email),)
        ).fetchone()
    return row is not None


def log_send(lead_id: int, to_email: str, subject: str) -> None:
    """Records a real (non-test) send."""
    now = datetime.now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sent_log (lead_id, to_email, subject, sent_at, sent_on) VALUES (?, ?, ?, ?, ?)",
            (lead_id, normalize_email(to_email), subject, now.isoformat(), now.date().isoformat()),
        )


def count_sent_today() -> int:
    from datetime import date
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM sent_log WHERE sent_on=?", (date.today().isoformat(),)
        ).fetchone()
    return row["n"]
