# Distribution Agent — Source of Truth

The single reference for what this agent actually does today. If this
file and the code ever disagree, **the code is right** — update this
file to match, not the reverse.

## Scope

Publishes a QC-approved video to one or more social platforms,
verifies it actually went live, and emails the client POC a
confirmation. Never runs on a video that hasn't already passed the
Quality Control Agent (see `QC_AGENT.md`).

## The one invariant: approval before posting

`distribute()` in `distribution_agent/distribution_agent.py` calls
`approve(platform, asset)` before every single upload. No approval
means no post — full stop:

- No flag or setting bypasses this.
- An unapproved platform is skipped entirely — its adapter is never
  even instantiated, so no credentials are touched and no API request
  is made for it.
- The default `cli_approval()` prompts on the terminal and **fails
  safe (denies)** on anything short of an explicit "y" — including a
  non-interactive terminal, silence, or EOF. It never crashes and
  never defaults to yes.
- To wire approval to something other than a terminal prompt (a
  dashboard button, a Slack confirmation), pass a custom
  `approve: (platform, asset) -> bool` callable to `distribute()`.

## Supported platforms

| Platform | Adapter | Credentials (env vars) | Setup effort | Expiry behavior |
|---|---|---|---|---|
| Bluesky | `adapters/bluesky.py` | `BLUESKY_IDENTIFIER`, `BLUESKY_APP_PASSWORD` | Simplest native — one App Password, no dev app or review, **but the account's email must be confirmed** or video upload 401s with `unconfirmed_email` | App Passwords don't expire on a timer |
| Reddit | `adapters/reddit.py` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_USER_AGENT`, `REDDIT_SUBREDDIT` | Register a "script" app, no review | Re-authenticates every run; watch for Reddit deprecating password-grant apps |
| YouTube | `adapters/youtube.py` | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Google Cloud project + one-time OAuth consent | Refresh token is long-lived **only once the app is out of "Testing" mode** — just 7 days while still in Testing |
| Facebook | `adapters/facebook.py` | `FB_PAGE_ACCESS_TOKEN`, `FB_PAGE_ID` | Meta Developer App + Page access token | Page token is effectively permanent unless revoked |
| Threads | `adapters/threads.py` | `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID` | Same Meta Developer App as Facebook/Instagram + Threads API product + its own OAuth scopes | Not yet characterized against a live account |
| Pinterest | `adapters/pinterest.py` | `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID` | Pinterest Developer app + one-time OAuth consent | Not yet characterized against a live account |
| Instagram | `adapters/instagram.py` | `IG_ACCESS_TOKEN`, `IG_BUSINESS_ACCOUNT_ID` | Meta Developer App + Business/Creator account + linked Page — the most setup steps of the native adapters | Long-lived token expires **~60 days** — must be refreshed before it lapses, or the OAuth consent flow has to be redone from scratch |
| LinkedIn | `adapters/uploadpost.py` (`LinkedInAdapter`) | `UPLOADPOST_API_KEY`, `UPLOADPOST_USER` | Routed through UploadPost.com — LinkedIn's own partner-approval process isn't self-serve | UploadPost manages the underlying token; not our concern |
| TikTok | `adapters/uploadpost.py` (`TikTokAdapter`) | `UPLOADPOST_API_KEY`, `UPLOADPOST_USER` | Routed through UploadPost.com — TikTok's own Content Posting API audit can take weeks | UploadPost manages the underlying token; not our concern |

Full step-by-step credential setup for each platform:
`SETUP.md`.

**Bluesky video upload — two real bugs found and fixed by testing against
a live account (2026-09-24), not by re-reading docs:**
1. The service-auth token's audience must be the account's own PDS
   (federated — varies per account, e.g. `did:web:discina.us-west.host.bsky.network`
   for this test account), not a fixed `did:web:video.bsky.app`. The
   correct value comes from `createSession`'s own response
   (`didDoc.service` where `id == "#atproto_pds"`) — see
   `BlueskyAdapter._pds_did_from()`.
2. That token must be scoped to lexicon method
   `com.atproto.repo.uploadBlob`, not the more obviously-named
   `app.bsky.video.uploadVideo` — the service's own 401 body named the
   expected method directly.

Both were only discoverable by reading the actual rejection response
bodies rather than assuming `raise_for_status()`'s generic error was
the whole story — worth remembering for any other adapter that starts
failing without an obvious cause.

`ThreadsAdapter` mirrors `InstagramAdapter`'s container→poll→publish
shape (same family of API, different product). Endpoint and field
names (`graph.threads.net/v1.0`, container `status` values, the
`error_message` field, the 24h container expiry) were confirmed
against Meta's current Threads API docs before writing it — not
guessed — but like Pinterest, it hasn't been exercised against a live
account in this codebase yet.

`LinkedInAdapter` and `TikTokAdapter` are both thin subclasses of one
shared `UploadPostAdapter` implementation — same endpoint, same
multipart shape, differing only in the `platform` field value. Unlike
every native adapter, `UploadPostAdapter.verify_live()` can only trust
the upload response itself (UploadPost's docs don't expose a
get-post/status endpoint) — a genuinely weaker live-confirmation
guarantee than the rest. Its endpoint/field names also haven't been
exercised against a live UploadPost account in this codebase yet —
confirm against their current docs before relying on it in production.

## `.env` loading

`distribution_agent/__init__.py` calls `load_dotenv()` on import, so
values in a project-root `.env` file are picked up automatically —
no manual `load_dotenv()` call or shell `export` needed before using
the package. (This was a real gap until 2026-09-24: `config.py` only
ever read `os.environ` directly, so `.env` values silently weren't
seen unless the caller loaded them itself.)

## `VideoAsset` contract

Defined in `distribution_agent/adapters/base.py`:

- `local_path` — required by YouTube, Reddit, Bluesky, Pinterest,
  LinkedIn, and TikTok (they all upload the file directly).
- `public_url` — required by Instagram and Threads (both fetch the
  video server-side, they can't accept a local file); Facebook accepts
  either `local_path` or `public_url`.

## Output

One `DistributionRecord` per platform: `platform`, `approved`,
`post_id`, `url`, `is_live`, `poc_notified`. `is_live` is only set
after `verify_live()` re-fetches the post from the platform itself — a
successful upload response alone doesn't count as confirmation.

## Not yet built

**Snapchat — confirmed not possible, not just unbuilt.** Verified
against Snap's current docs (2026-09-25): their Marketing/Ads API is
paid-campaigns-only, and Creative Kit (the other candidate) is
client-side-only — it opens the Snapchat app on a real person's own
device for them to manually review and send, and cannot be triggered
unattended from a backend. There is no programmatic organic-posting
surface to build against at all. UploadPost doesn't list Snapchat
either, independently confirming this. Unlike everything else on this
list, this isn't a "not yet built" gap — there's nothing to build.

X/Twitter (no approval gate, but real per-request cost — pay-per-usage
credits, ~$0.015/post, no subscription; see `CURRENT_OBSTACLES.md` for
the full cost comparison against routing it through UploadPost
instead — decision not yet made) could follow either pattern already
established — a native adapter, or a thin `UploadPostAdapter`
subclass if UploadPost also covers it and the native path is gated.

## Related files

- Prompt spec: `agent-prompts.md` (section 2)
- Implementation: `distribution_agent/`
- Credential setup walkthrough: `SETUP.md`
