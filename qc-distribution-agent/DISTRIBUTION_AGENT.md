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
| Reddit | `adapters/reddit.py` | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_USER_AGENT`, `REDDIT_SUBREDDIT` | Needs Reddit's **explicit written approval** for commercial use (ticket pending since 2026-10-01), and the "script" app can't be created yet (reCAPTCHA failure); see `CURRENT_OBSTACLES.md` | Re-authenticates every run; watch for Reddit deprecating password-grant apps |
| YouTube | `adapters/youtube.py` | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Google Cloud project + one-time OAuth consent | Refresh token is long-lived **only once the app is out of "Testing" mode** — just 7 days while still in Testing |
| Facebook | `adapters/facebook.py` | `FB_PAGE_ACCESS_TOKEN`, `FB_PAGE_ID` | Meta Developer App + Page access token | Page token is effectively permanent unless revoked |
| Threads | `adapters/threads.py` | `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID` | Same Meta Developer App as Facebook/Instagram + Threads API product + its own OAuth scopes | Not yet characterized against a live account |
| Pinterest | `adapters/pinterest.py` | `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID` | Pinterest Developer app + one-time OAuth consent. New app is waiting on **Trial access** (app secret withheld until approved); real posting needs Standard access, and ToS 2.3 requires Pinterest's app review before use; see `CURRENT_OBSTACLES.md` | Not yet characterized against a live account |
| Instagram | `adapters/instagram.py` | `IG_ACCESS_TOKEN`, `IG_BUSINESS_ACCOUNT_ID` | Meta Developer App + Business/Creator account + linked Page — the most setup steps of the native adapters | Long-lived token expires **~60 days** — must be refreshed before it lapses, or the OAuth consent flow has to be redone from scratch |
| X | `adapters/x.py` | `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_REFRESH_TOKEN` | Native — confidential client + OAuth 2.0 PKCE consent; no approval gate, but needs a funded pay-per-usage credit balance | Access tokens short-lived, refreshed per call. Refresh token itself expires in **~6 months** (per X's console UI at generation time) — longest-lived of any credential in this pipeline. Rotation-on-use still unconfirmed by X's docs, handled defensively regardless (see below) |
| LinkedIn | `adapters/linkedin.py` | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_ID` | Native as of 2026-10-01 — posts to a **personal profile** (`w_member_social`), not a Company Page; see `CURRENT_OBSTACLES.md` for why (Company Page creation hit a connections/profile-strength gate this account hadn't cleared) | Access tokens last ~60 days; this adapter doesn't refresh them (LinkedIn's refresh-token support is its own separate approved product, not assumed granted) — expiry means redoing the OAuth flow manually |
| TikTok | `adapters/tiktok.py` | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN` | Native as of 2026-10-01, via the Content Posting API (Direct Post) — requires the Login Kit product as a platform-enforced dependency even for posting to your own account, and a formal app review (demo video against Sandbox required) before it works beyond Sandbox test accounts; see `CURRENT_OBSTACLES.md` | Verified end-to-end in Sandbox only (2026-10-02): private account, posts forced to `SELF_ONLY`. Access tokens are short-lived and the last one is expired, so refresh before testing. App review not submitted. Direct Post's UX requirements aren't met by this headless pipeline; see `CURRENT_OBSTACLES.md` |

Both LinkedIn and TikTok were originally routed through UploadPost.com (`adapters/uploadpost.py`'s `UploadPostAdapter`, still present as a fallback, just no longer registered in `ADAPTERS` by default) specifically to avoid each platform's own approval process. Switched to native 2026-10-01 — see `CURRENT_OBSTACLES.md` for the full reasoning and the real gates each native path turned out to have anyway (LinkedIn's connections requirement, TikTok's audit).

Live status as of 2026-10-05: Instagram verified. YouTube, Bluesky and X verified earlier. Facebook's Page token is dead (Graph error 190) and needs regenerating. LinkedIn is untested because it's blocked on the Company Page requirement. Reddit, Pinterest and Threads are blocked on approvals or account decisions. Details are in `CURRENT_OBSTACLES.md`.

`TikTokAdapter.upload()` defaults `privacy_level` to `SELF_ONLY` — TikTok restricts unaudited apps to private/self-visible posts regardless of what's requested, confirmed in the App Review flow's own guidance. Don't change this default until the app is actually approved.

`LinkedInAdapter.upload()` follows LinkedIn's Videos API (`initializeUpload` → chunked `PUT` to the returned upload URL(s), capturing each part's `ETag` → `finalizeUpload`) then creates the post via the Posts API (`POST /rest/posts` referencing the video URN). Endpoint/field names confirmed against LinkedIn's current docs (`learn.microsoft.com/.../videos-api`, `.../posts-api`) before writing, not guessed.

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

`XAdapter` uses OAuth 2.0 Authorization Code + PKCE (chosen over OAuth
1.0a since it matches the refresh-token pattern already used for
YouTube). Endpoint/field names for chunked media upload
(INIT/APPEND/FINALIZE/STATUS) and the token endpoint were confirmed
against X's current docs before writing this. One thing the docs
didn't confirm: whether refresh tokens rotate on use. Handled
defensively regardless — `_get_access_token()` writes any new
`refresh_token` a refresh response includes back into `.env`
automatically (via `python-dotenv`'s `set_key()`), so this doesn't
silently break if rotation turns out to be real.

In practice, the first real credential was generated through X's
console UI directly ("Generate OAuth 2.0 Access Token" on the app's
Keys page) rather than via `get_x_token.py`'s PKCE flow — X apparently
offers this as a first-party shortcut for authorizing your own
account. One open question from doing it that way: the console's
scope checklist doesn't offer `media.write` as an option at all
(only `tweet.write`/`tweet.read`/`users.read` plus DM/follow/
engagement/list scopes), even though X's docs say media upload
requires it. Unconfirmed whether it's bundled into `tweet.write`
automatically for this flow, or genuinely absent — will only be known
for certain once a real video upload is attempted. If it turns out
missing, `get_x_token.py`'s PKCE flow explicitly requests
`media.write` and is the fallback.

`UploadPostAdapter` (`adapters/uploadpost.py`) is kept as an
unregistered fallback for LinkedIn and TikTok. Unlike the native
adapters, its `verify_live()` can only trust the upload response,
because UploadPost's docs don't expose a status endpoint, so its
live-confirmation guarantee is weaker. Its endpoint and field names
haven't been exercised against a live UploadPost account, so check
them against their current docs before relying on it.

## `.env` loading

`distribution_agent/__init__.py` calls `load_dotenv()` on import, so
values in a project-root `.env` file are picked up automatically —
no manual `load_dotenv()` call or shell `export` needed before using
the package. (This was a real gap until 2026-09-24: `config.py` only
ever read `os.environ` directly, so `.env` values silently weren't
seen unless the caller loaded them itself.)

## `VideoAsset` contract

Defined in `distribution_agent/adapters/base.py`:

- `local_path` — required by YouTube, Reddit, Bluesky, Pinterest, X,
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

## Related files

- Prompt spec: `agent-prompts.md` (section 2)
- Implementation: `distribution_agent/`
- Credential setup walkthrough: `SETUP.md`
