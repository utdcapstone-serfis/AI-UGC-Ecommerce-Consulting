# Serfis lead-gen: system guide (current as of 2026-10-17)

This replaces the PDF in `brand/`, which was written before the verified-contact rule, the guardrails and the
company-record dashboard. Everything here describes the code on this branch.

## 1. What it does, and the two rules everything else follows

Serfis sells short-form video ads and social content to early-stage tech startups. The system finds those startups,
checks they fit, finds a decision-maker, researches them and drafts a personal first email.

1. **A person approves every email.** Nothing is sent unless a lead is approved *and* the send step is run.
2. **A company is only a lead if its contact is verified.** No guessed and no data-provider emails (section 4).

## 2. The pipeline and the nine agents

`orchestrator.py` runs them in this order for each company and saves after every step.

| # | Agent | File | Job |
|---|---|---|---|
| 1 | Discovery | `agents/discovery.py`, `yc_pool.py`, `yc.py` | Candidates from the YC F26 prospect tracker (`data/target_companies.csv`, P1 then P2), then from 11 recent YC batches (open yc-oss dataset). Free ICP pre-screen; ranking learns from past lookups (`lookup_history`) |
| 2 | Enrichment | `agents/enrichment.py`, `classify.py` | Size band, industry, location, what they sell; YC profile facts (team size, batch, founders) |
| 3 | ICP guardrail | `agents/icp.py` | Rejects poor fits before any paid step: research-only comparables, developer tools/infrastructure (e.g. SDKs), services firms, over 200 people, no startup evidence. Fails closed |
| 4 | Contact finder | `agents/contact_finder.py`, `site_emails.py`, `linkedin.py` | One decision-maker with a verified email (section 4). No contact means the company is dropped |
| 5 | Scoring | `agents/scoring.py` | ICP score 1-10 (tracker fit rating sets it; else Claude or a rule score) |
| 6 | Research | `agents/research.py` | Public website + YC profile; observations, sources, content angle, best ad type |
| 7 | Outreach writer | `agents/outreach_writer.py` | First-touch draft in the "Allison / Serfis AI" voice; email only, never a call, meeting or demo. Draft only |
| 8 | Reply writer | `agents/reply_writer.py` | Drafts a reply when a person pastes a prospect's reply; unsubscribe requests are suppressed, not answered |
| 9 | Send agent | `agents/send_agent.py` | Sends approved leads through Gmail, only from the CLI, with every guardrail |

Without `ANTHROPIC_API_KEY`, scoring reasons, research and drafts use built-in rules and templates.

## 3. Discovery in numbers (2026-10-16)

1,977 YC companies scanned; 1,337 screened out by the ICP rules; 608-618 eligible; 51 publish a founder email on their own
site (about 5%); 16 leads saved. A strict rule means a trickle of leads, so discovery is wide and free.

## 4. The verified-contact rule

A lead needs a **named decision-maker** whose email is one of:
- **published** by the company on its own domain (home, contact, about, team, press, careers, legal, `security.txt`... 18 paths);
- **linkedin**: written by the founder in their own LinkedIn headline, About or role text (`email_status = linkedin`);
- **confirmed** by a person (`python main.py confirm-email <id>`).

And, unless confirmed by a person, LinkedIn must show the contact **currently holds a decision-making role** at that company
(`agents/linkedin.py`; no-email mode; the tool's own email finder is never read: it only guesses).

Never accepted: provider-found emails (Apify leads add-on), guessed first-name addresses, verifier-tool "valid" results
(every Google Workspace domain comes back "risky" even for made-up addresses), the LinkedIn Contact-info button (needs a login and only shows
connections). The sender refuses any other status even if one slips into the database.

`python main.py audit-contacts [--repoint]` re-checks every lead and stores the proof in `contact_check`.

## 5. Guardrails (`agents/guardrails.py`)

- **Draft quality:** unfilled `[placeholders]`/NEEDS_ENRICHMENT, wrong length (80-210 words), greeting without the contact's first name,
  company never named, any ask for a call/meeting/demo, "autonomous"/"AI pipeline" self-description, garbling like "aI native",
  percent/dollar claims not found in the research.
- **Bounce and complaint breaker + kill switch:** auto-pauses sending at 2+ bounces and a 5% rate over 14 days, or any spam complaint.
  `pause` / `resume` are the manual switch (flag file `output/SENDING_PAUSED`). Bounced addresses join the do-not-contact list.
- **One touch per company:** no second email to the same company within 90 days, even to a different founder.
- **Location:** outside the US or unknown needs a human OK (EU, UK, Canada get a specific warning; Germany is especially strict).
- A flagged lead can only be approved with an explicit **Approve anyway**, recorded in `leads.overrides`; the sender re-checks at send time.
- Also: daily send cap (default 20), pause between emails, opt-out line and postal address on every email, `MAILING_ADDRESS` required
  for real sends, suppression list, send log.

## 6. The dashboard (`python app.py`, http://127.0.0.1:5050)

- **Home:** five stat cards, the **manual approval queue** bar (waiting / approved / sent / rejected), filters, and the lead table with a Checks column.
  Amber edge = waiting on you.
- **Click a company:** its full record opens at the top of the same page (`/?lead=<id>`, fragment at `/panel/<id>`): sticky approval strip, hero with
  avatar and ICP ring, **AWAITING YOUR APPROVAL / APPROVED BY YOU / REJECTED BY YOU** banner, five-step path (the manual step highlighted), four readiness
  tiles, guardrail checks, contact card with the verification proof and copy button, company and ICP facts, research, the draft as an email, an activity
  timeline, analytics, lead status, conversation, and a collapsible **Complete record** listing every stored field.
- Approving only records your decision (and `decided_at`). Sending is a separate command. Version marked by the git tag `dashboard-v1-lead-gen`.
- `/lead/<id>` (the old separate page) still works; `/export` downloads the Excel list.

## 7. Commands

`run [--limit N] [--max-lookups N]` · `review` · `approve <id> [--force]` · `reject <id>` · `confirm-email <id> [--email x]` ·
`audit-contacts [--repoint]` · `checks` · `pause ["reason"]` · `resume` · `bounce <email>` · `complaint <email>` ·
`check-bounces [--days N] [--dry-run]` · `send <id> [--to test@x.com]` · `send-approved [--limit N] [--dry-run]` · `suppress <email>` ·
`export` · `seed-demo` · `reset` (deletes all leads, asks first).

## 8. Settings (`.env`; secrets are never committed)

`APIFY_API_TOKEN` · `ANTHROPIC_API_KEY` (not set today) · `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` · `MAILING_ADDRESS` (not set: real sends blocked) ·
`EMAIL_DAILY_CAP` 20 · `EMAIL_SEND_DELAY_SECONDS` 45 · `REQUIRE_VERIFIED_CONTACT` true · `LINKEDIN_VERIFY` true · `LINKEDIN_ACTOR`
(`apimaestro/linkedin-profile-detail`) · `LINKEDIN_EMAILS` true / `LINKEDIN_SCAN_MAX_PROFILES` 0 · `PAID_LOOKUP_FALLBACK` false ·
`GUESS_FOUNDER_EMAILS` false · `MAX_LOOKUPS_PER_RUN` 30 · `BOUNCE_*` and `COMPANY_COOLDOWN_DAYS` 90 · `DEMO_MODE` · `PORT` 5050.

## 9. Data

SQLite at `output/leads.db` (git-ignored): `leads`, `platform_analytics`, `messages`, `suppressions`, `sent_log`, `lookup_history`, `risk_events`.
`snapshots/` holds a copy of the database and the Excel list from 2026-10-17 (contains founders' business emails: keep the repo private).
`docs/run-logs/` has the two wide pipeline runs.

## 10. Tools, limits and costs

- **Apify free plan:** $5/month credit (about $2.05 used by 2026-10-16). Website scanning and the YC dataset are free.
- **LinkedIn profile tools:** `harvestapi/linkedin-profile-scraper` is capped at **50 runs in total** on the free tier; `apimaestro/linkedin-profile-detail`
  ($0.005 per profile) at **20 profiles per day**. A refusal arrives as an item with `error` or `message`; it is a transient tool failure, never a verdict
  on a company. An Apify paid plan removes both caps.
- Reading LinkedIn goes against its terms of service even without logging in; here it is a narrow role check and text the founder wrote.
- Email verifier actor and Google-search actor were tested and rejected (section 11).

## 11. Decisions and lessons

- Human approval stays; "fully autonomous sending" was declined as the first design. Autonomy is staged (section 12).
- Provider emails looked fine but were not verifiable; guessing patterns was the rejected shortcut. Published-by-the-company is the strongest available evidence.
- **Rejected sources:** GitHub commit emails (GitHub's terms forbid using them for unsolicited email); web search for `@domain` (1 hit in 4 tries, $0.0045 each);
  paid SMTP verifiers (Google Workspace always "risky"); port-25 checks (blocked on this network).
- Mistakes worth remembering: a full database reset once deleted real leads (hence backups and the `reset` confirmation); tool failures were once recorded as
  verdicts (42 companies wrongly rejected); a swallowed HTTP 400 hid that Apify's minimum per-run cap is $0.50; a regex replace made a helper call itself.
- Test with real data: the draft check caught real "aI native" drafts that unit tests had missed.

## 12. Known limits and the path to autonomy

No live inbox (replies are pasted in); no scheduler (the dashboard and pipeline run only while the computer is on); no follow-up agent; no send-window or
ramp-up rule yet; bounce detection from Gmail is tested only on a synthetic notice. Next: host + schedule the pipeline with a spend cap and alerts; auto-approve
rules for clean leads; send windows and a slow ramp (3-5 a day); real DMARC and mailing address; inbox bounce/reply reading; follow-ups that stop on any reply;
a results dashboard feeding scoring. Replies stay human-approved.

## 13. Tests and layout

`python tests/test_guardrails.py` (60 checks) and `python tests/test_verified.py` (34): throwaway DB, no billing.
Layout: `agents/` · `templates/` + `static/` (dashboard) · `data/` (seed + tracker) · `tests/` · `docs/` · `snapshots/` · `brand/` (PowerPoint template, agents slide, old PDF).
Video and Higgsfield work lives on the `Allison-Higgsfield` branch.
