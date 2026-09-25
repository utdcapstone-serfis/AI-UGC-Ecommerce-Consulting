# Serfis Lead-Gen Agent + Dashboard (MVP)

Autonomous pipeline that discovers SaaS/SMB/recently-funded companies,
enriches and scores them against Serfis's ICP, finds a point of contact,
researches personalized angles, and drafts a first-touch outreach email -
plus a Flask web dashboard for a human to review, filter, approve/reject,
and export those leads. **Nothing is ever sent automatically** - every lead
sits at `approval_status = pending_review` until a human approves it, and no
code path in this repo calls an email/SMS provider.

```
Lead Finder -> Enrichment -> ICP Scoring -> Contact Finder -> Research ->
Outreach Writer -> SQLite -> Serfis Lead Dashboard -> Human Review ->
Approve/Reject -> Excel Export -> (future) Approved Lead -> Send Agent
```

## File layout

```
serfis-leadgen/
  config.py              # env-based settings, DEMO_MODE switch, Serfis pitch text
  models.py               Lead dataclass (matches the required output block)
  storage.py               SQLite persistence + query/filter/sort (output/leads.db)
  orchestrator.py          Chains all agents together per company
  export_excel.py          Exports the DB to output/serfis_leads.xlsx
  main.py                   CLI entrypoint (pipeline + review/approve/reject/export/seed-demo/reset)
  app.py                    Flask dashboard (reads/writes the same leads.db)
  demo_seed.py              NEW - seeds the one fictional "converted" lead + its analytics
  templates/                dashboard.html, lead_detail.html, base.html
  static/
    style.css                dashboard styling
  agents/
    discovery.py           Step 1: find companies (seed CSV or Apify Crunchbase actor)
    apify_client.py         Shared Apify Actor-runner
    scraper.py              Shared website-text fetcher
    enrichment.py           Step 2: industry/size/location/what-they-sell
    scoring.py               Step 3: ICP fit score 1-10 + reasoning
    contact_finder.py       Step 4-5: point of contact (Apify/Hunter, or NEEDS_ENRICHMENT)
    research.py              Step 6: 2-3 personalized observations + sources
    outreach_writer.py       Step 7: drafts the email (75-125 words)
    send_agent.py             Phase 2 stub - NOT wired up, sending is off by default
    llm.py                     Shared Claude API wrapper
  data/
    seed_companies.csv       Demo-mode company list (used when no discovery API key set)
  output/
    leads.db                  SQLite DB (created/migrated automatically on first run)
    serfis_leads.xlsx          Excel export (created on export)
```

**Current database state:** `output/leads.db` has been reset to empty (no
real leads have been run yet) plus exactly **one fictional sample lead**,
"Northwind Outfitters (Sample)", seeded by `demo_seed.py` so the dashboard
has something to demonstrate - including the content analytics view - without
implying any real company was actually contacted. See "Sample converted lead
& content analytics" below.

**What's new in this pass:** `app.py`, `templates/`, `static/style.css`,
`demo_seed.py`, a new `platform_analytics` table, and two additive columns on
the existing `leads` table (`lead_status`, `research_sources` - see "Schema
changes" below). Nothing in `orchestrator.py` or `agents/*` (besides
`research.py` now also populating `research_sources`) was rewritten or
restructured.

## Setup

Requires Python 3.10+.

```bash
cd serfis-leadgen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `ANTHROPIC_API_KEY` - recommended even in demo mode, powers enrichment/research/email quality. Without it, the pipeline falls back to simple heuristic/template logic so it still runs end to end.
- `APIFY_API_TOKEN` / `HUNTER_API_KEY` - add these to leave demo mode and do real company discovery + real contact lookup. Without them, the agent uses `data/seed_companies.csv` for discovery and marks contact fields `NEEDS_ENRICHMENT` rather than inventing a person's name/email. Discovery and contact-finding both run through Apify Actors by default - see "Apify integration" below for which ones and why.

## Running the pipeline (unchanged)

```bash
python main.py run --limit 5      # run the full pipeline end to end
python main.py review             # print all leads pending approval
python main.py approve 3          # mark lead id 3 approved (still doesn't send anything)
python main.py reject 3           # mark lead id 3 rejected
python main.py export             # (re)generate output/serfis_leads.xlsx
python main.py seed-demo          # add the one fictional sample lead + analytics (idempotent)
python main.py reset              # delete ALL leads and analytics (asks "yes" to confirm; --yes skips it)
```

Every run upserts into `output/leads.db` keyed on (company_name, website), so re-running is safe and just refreshes existing rows. Running `python main.py run` right now will add real leads alongside the sample one - that's expected, the sample is just there to show the analytics view until real leads exist.

## Apify integration

Discovery and contact-finding both run through [Apify](https://apify.com)
Actors (previously Apollo.io - replaced per sponsor direction). Both agents
call `agents/apify_client.run_actor()`, a thin wrapper around Apify's
`run-sync-get-dataset-items` REST endpoint - it starts an Actor, waits for it
to finish, and returns its output dataset directly.

| Purpose | Actor (config.py default) | Reliability |
|---|---|---|
| Contact-finding | `vdrmota/contact-info-scraper` | Well-established: Apify-maintained, 60K+ users, 13M+ runs, 4.7★. Extracts only what a company has published on its own site (no LinkedIn scraping). |
| Company discovery | `automation-lab/crunchbase-company-funding-search-scraper` | **Unproven** - 14 users, no reviews at the time this was wired up. It was the closest fit to "search Crunchbase by keyword, filter to companies with funding," but nothing on Apify matches Apollo's maturity for structured company discovery. |

Both Actor ids are overridable via `.env` (`APIFY_DISCOVERY_ACTOR`,
`APIFY_CONTACT_ACTOR`) without touching code, in case either needs swapping
out later.

**Known gap - validate before relying on this:** the discovery Actor's
*input* schema (`queries`, `maxItems`, `requireFunding`) was confirmed
directly from its published schema, but the exact *output* field names
were not confirmed against a real run before a token was available.
`DiscoveryAgent._parse_result()` and `ContactFinderAgent._parse_result()`
both check a few likely field-name variants defensively, but - exactly like
the real bugs we found and fixed in the old Apollo integration by actually
running it - **run this for real once you have an `APIFY_API_TOKEN` and
check that leads are coming back with real names/websites/emails, not
silently empty results.** If the field names are wrong, `_parse_result()`
is the only place that needs fixing.

## Video ad generation (Higgsfield)

`.claude/skills/higgsfield/` is a Claude Code Skill (not a Python agent) for
generating AI video/image ads via [Higgsfield](https://higgsfield.ai) -
Seedance, Kling, Wan, Genjutsu, and other model families. Needs two
credentials in `.env` (`HIGGSFIELD_API_KEY_ID` and
`HIGGSFIELD_API_KEY_SECRET` - note it's two separate values, not one). The
skill itself explains the request lifecycle, cost-estimation, and - most
importantly - to always confirm the exact request schema from the specific
model's own docs page rather than guessing, since it varies per model.

This is separate from the lead-gen pipeline above: it doesn't touch
`storage.py`'s leads table or get triggered by anything automatically. It's
a capability Claude can use when asked to generate ad creative, optionally
grounded in a specific lead's data if asked to make something for/about
that company.

## Running the dashboard (new)

```bash
cd serfis-leadgen
source venv/bin/activate          # if not already active
python app.py
```

Then open **http://localhost:5050** in a browser.

- The dashboard reads/writes the exact same `output/leads.db` the pipeline
  uses - run `python main.py run` first (or at any point) to populate leads,
  then refresh the dashboard to see them.
- Default port is **5050**, not Flask's usual 5000, because macOS's AirPlay
  Receiver squats on 5000 by default and silently refuses connections there.
  Override with `PORT=xxxx python app.py` if you need a different port.
- The first request auto-runs a schema migration (`storage.init_db()`) that
  adds the two new columns to an existing `leads.db` in place - no data is
  lost, no manual migration step needed.
- Stop the server with `Ctrl+C`.

### Dashboard walkthrough

- **Home (`/`)** - five summary cards (Total, Qualified `score>=7`, Pending
  Review, Approved, Rejected), then the lead table. Search by company name,
  filter by ICP score / Lead Status / Approval Status / Industry, sort by
  ICP score high-to-low or low-to-high - all server-side via query params, no
  JS framework needed. Click any row to open that lead.
- **Lead detail (`/lead/<id>`)** - every field from the required output
  block (company info, ICP score + reasoning, contact, research notes +
  sources, funding notes, outreach angle, full draft email subject/body),
  plus:
  - **Approve Outreach** / **Reject Outreach** buttons - each is a plain
    HTML form POST that calls `storage.set_approval_status()`, the exact
    same function `main.py approve/reject` already used. Neither button
    sends anything.
  - **Lead Status** dropdown (`New` / `Contacted` / `Qualified` /
    `Disqualified`) + **Update Status** button - a separate field from
    approval status, for tracking where a lead actually is in the outreach
    lifecycle (e.g. mark `Contacted` once a human sends the approved email
    themselves, today, by hand).
- **Export to Excel** (top nav, or `/export`) - calls the existing
  `export_excel.export_to_excel()` unmodified and streams the resulting
  `.xlsx` back as a download.
- **Content Performance Analytics** (on the lead detail page, below the
  draft email) - a card per platform (Facebook, Instagram, YouTube, X,
  Reddit) showing Views / Likes / Shares / Comments. Empty for every normal
  lead ("No published content yet..."); populated only for the sample lead
  (see below) as a demonstration of where this goes once a lead converts and
  Serfis-produced content is actually live.

## Sample converted lead & content analytics

You asked to see what a *converted* lead looks like, including the video/social
analytics view, without any real leads in the system yet. `demo_seed.py`
creates exactly one fictional lead for this:

- **Company:** "Northwind Outfitters (Sample)" - a made-up DTC apparel brand,
  website `northwindoutfitters.example` (the `.example` TLD is reserved by
  RFC 2606 specifically so it can never resolve to a real site).
- Every field (contact, research notes, email draft, funding) is clearly
  fictional/illustrative - no real company's data was used or implied.
- `lead_status = 'converted'`, `approval_status = 'approved'`, and it has one
  row per platform in the new `platform_analytics` table with made-up
  Views/Likes/Shares/Comments numbers.
- It's tagged `source = 'demo_sample'` in the database, which the dashboard
  uses to render a black **SAMPLE** badge next to it everywhere it appears
  (lead table, lead detail header) plus a banner on its detail page - so it's
  never mistaken for a real prospect, in the UI or in an Excel export.
- Regenerate it any time with `python main.py seed-demo` (safe to re-run -
  it upserts the same record); remove everything including it with
  `python main.py reset`.

**Where the real data will come from later:** `platform_analytics` is
populated by `demo_seed.py` today with illustrative numbers only. A future
`ContentAnalyticsAgent` would instead call each platform's real API
(Facebook/Instagram Graph API, YouTube Data API, X API, Reddit API) for
content actually published for converted customers, then call
`storage.upsert_platform_analytics()` - the same function the demo seed uses
- with real numbers on a schedule.

## Schema changes

Two columns were added to the `leads` table, both additive (existing rows
get a default value, nothing is dropped or renamed), plus one new table:

| Column/Table | Values | Set by |
|---|---|---|
| `leads.lead_status` | `new` (default) / `contacted` / `qualified` / `disqualified` / `converted` | Dashboard "Update Status" dropdown, or `demo_seed.py` for the sample lead |
| `leads.research_sources` | free text, e.g. "Company website (https://...)" | `ResearchAgent`, automatically, on each pipeline run |
| `platform_analytics` (new table) | `lead_id`, `platform`, `views`, `likes`, `shares`, `comments` | `demo_seed.py` today; a future analytics agent, going forward |

`approval_status` (`pending_review` / `approved` / `rejected`) is unchanged
in meaning and is still the field the CLI's `approve`/`reject` commands and
the dashboard's Approve/Reject buttons both write to - so a lead approved
from the CLI shows as Approved in the dashboard and vice versa, since both
read/write the same table through the same `storage.py` functions.

(One prior value, `sent`, was never actually reachable - `send_agent.py` was
always a stub - so it was retired in favor of `lead_status='contacted'`,
which the future send agent should set instead once it's implemented.)

## Human-approval workflow (unchanged, now with a UI)

1. `python main.py run` produces drafts with `approval_status = pending_review`.
2. Open the dashboard at `http://localhost:5050` (or `python main.py review`
   / `output/serfis_leads.xlsx` from the CLI, still works) and read each draft.
3. Click into a lead and press **Approve Outreach** or **Reject Outreach**.
4. **Sending is still not implemented.** `agents/send_agent.py` is a stub
   that isn't imported anywhere in the pipeline or the dashboard, and
   refuses to run against anything not `approved`. When you're ready for
   Phase 2, wire it to an ESP (SendGrid/Postmark/Gmail API), have it set
   `lead_status='contacted'` on success, and add an explicit, off-by-default
   trigger (CLI flag and/or a "Send" button gated to `approved` leads only).

## Conversation / reply drafts

Once a prospect replies to the first-touch email, `ReplyDraftAgent`
(`agents/reply_writer.py`) can draft a suggested response - but it never
sends anything and it never runs on its own. The flow, all on the lead
detail page under "Conversation":

1. There is no live inbox connection yet, so a human logs the prospect's
   actual reply by pasting it into the "Log a reply from this prospect" form.
2. That save triggers `ReplyDraftAgent.draft_reply()`, which reads the
   original outreach email plus the prospect's reply and drafts a response -
   Claude-written if `ANTHROPIC_API_KEY` is set, otherwise a safe template
   fallback that explicitly declines to guess at things like pricing and
   offers a human follow-up instead.
3. The draft is stored as a new `messages` row with `approval_status =
   'pending_review'` - same lifecycle, same table of allowed values
   (`pending_review`/`approved`/`rejected`) as the first-touch email.
4. A human reviews it in the thread and clicks **Approve Reply** or
   **Reject Reply**. Approving only updates the database - still nothing is
   sent.

This was a deliberate, discussed tradeoff: "fully autonomous" send-and-reply
was explicitly requested and explicitly declined, for the same reason
automatic first-touch sending was never implemented - an unsupervised AI
conversing with a real prospect can say something wrong with nobody catching
it first. This gives you a drafted reply for every conversation turn while
keeping a human decision in the loop each time.

**Not yet built:** a live inbox connection (Gmail API/IMAP) that would
auto-detect a prospect's reply instead of requiring it to be pasted in
manually. That's a real, separate integration - see "What remains as a
future enhancement" below.

## Ethical/legal notes on contact data

- No LinkedIn scraping - it violates LinkedIn's ToS. The Apify contact-finding Actor (`vdrmota/contact-info-scraper`) only extracts what a company has published on its own public site (contact/about pages) - it does not scrape LinkedIn profiles. Hunter.io, the fallback, is a licensed data provider.
- The pipeline never fabricates a real person's name/email. If no provider key is set, or a provider finds nothing, contact fields are explicitly marked `NEEDS_ENRICHMENT` instead of guessing.
- Website scraping is limited to simple GETs on public marketing pages with a descriptive User-Agent - no bypassing auth, paywalls, or bot protection.

## What's complete

- Full pipeline: discovery -> enrichment -> ICP scoring -> contact finder -> research -> outreach draft -> SQLite (unchanged from prior milestone).
- Dashboard: view all leads, search by company name, filter by ICP score/Lead Status/Approval Status/Industry, sort by ICP score, full lead detail view with every required field, Approve/Reject buttons wired to the database, Lead Status control, Excel export button.
- Content Performance Analytics view per lead (Facebook/Instagram/YouTube/X/Reddit), with one fully-populated fictional sample lead demonstrating it end to end.
- Shared database: CLI and dashboard read/write the same `leads.db` through the same `storage.py` functions, so state never diverges between them - verified live in this session by running `python main.py run` while the Flask server was up and confirming the new leads appeared on refresh with no restart.
- `output/leads.db` reset to its intended starting state: no real leads (none have been run for real yet), plus the one clearly-labeled sample lead.
- Verified end-to-end in this session: ran the Flask app against the real `output/leads.db`, exercised search, every filter, sorting, the Approve/Reject/status-update endpoints, live pipeline-to-dashboard sync, and the Excel export - all confirmed via direct DB reads after each action.

## What remains as a future enhancement

- **Real analytics data**: today `platform_analytics` only has illustrative numbers from `demo_seed.py`. A `ContentAnalyticsAgent` that calls each platform's real API for actually-published content is the natural next step - `storage.upsert_platform_analytics()` is already the write path it would use.
- **Automated sending**: implement `agents/send_agent.py` against an ESP, gated on `approval_status == 'approved'`, triggered explicitly (never automatically).
- **Auth**: the dashboard currently has no login - fine for a local/internal capstone demo, but add one (Flask-Login + a users table, or put it behind your school's SSO) before pointing it at real prospect data on a shared network.
- **CRM integration**: new `agents/crm_sync.py` pushing approved/contacted leads to HubSpot/Attio/Salesforce.
- **Follow-up sequences**: a `FollowUpAgent` that schedules N-day-later touches keyed off `lead_status='contacted'` + no reply.
- **Better lead scoring**: swap `ScoringAgent`'s heuristic/single-call logic for a model trained on your actual closed-won data.
- **Better discovery**: the Apify Crunchbase Actor is low-usage/unproven (see "Apify integration" below) - validate it against real output, or swap in a more established Actor/provider if it doesn't hold up at scale.
- **Pagination**: the lead table currently renders every matching row - fine at MVP volume, add LIMIT/OFFSET paging in `storage.query_leads()` once lead counts grow large.
- **Concurrency**: `orchestrator.py` still processes leads sequentially; each agent is stateless enough to parallelize once volume matters.
- **Postgres/Airtable**: swap `storage.py`'s sqlite3 calls for a hosted DB once you need true multi-user concurrent access to the review queue.
