# Distribution Agent — Platform Setup

Each platform requires you to obtain credentials yourself (OAuth
consent has to be granted by a logged-in human — this can't be
scripted). Once you have them, put them in `.env` (copy from
`.env.example`) and never commit that file.

## Instagram

1. Convert the target account to a **Business or Creator** account
   (Instagram app → Settings → Account type).
2. Link it to a **Facebook Page** (any minimal Page works).
3. Create a Meta Developer App at https://developers.facebook.com,
   add the **Instagram Graph API** product.
4. Run the OAuth flow yourself (Graph API Explorer or your app's login
   flow) granting `instagram_basic` and `instagram_content_publish`,
   then exchange for a **long-lived token**
   (`GET /oauth/access_token?grant_type=fb_exchange_token...`).
5. Fill in `IG_ACCESS_TOKEN` and `IG_BUSINESS_ACCOUNT_ID`.

Note: `InstagramAdapter.upload()` needs a **publicly reachable video
URL** (`VideoAsset.public_url`), not a local file — the Graph API
fetches the video from that URL itself.

## Facebook

1. Same Meta Developer App as above.
2. Generate a **Page access token** with `pages_manage_posts` and
   `pages_read_engagement`.
3. Fill in `FB_PAGE_ACCESS_TOKEN` and `FB_PAGE_ID`.

`FacebookAdapter.upload()` accepts either `VideoAsset.local_path` or
`VideoAsset.public_url`.

## YouTube

1. Create a Google Cloud project, enable **YouTube Data API v3**.
2. Create an OAuth 2.0 Client ID (Desktop app type is simplest).
3. Run the OAuth consent flow once, locally, with scope
   `https://www.googleapis.com/auth/youtube.upload`, to get a
   **refresh token** (e.g. via `google-auth-oauthlib`'s
   `InstalledAppFlow.run_local_server()`).
4. Fill in `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

New Google Cloud projects start in **testing mode** with a small quota
— request production access before relying on this for real traffic.

## Reddit

1. Register an app at https://www.reddit.com/prefs/apps (type:
   "script").
2. Fill in `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`,
   `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_USER_AGENT`,
   `REDDIT_SUBREDDIT`.

Reddit has been tightening password-grant OAuth for third-party apps —
if `RedditAdapter` stops authenticating, check current Reddit API docs
and switch to the web-app OAuth code flow.

## Bluesky

The simplest of the bunch — no developer app, no review process.

1. In the Bluesky app: **Settings → App Passwords → Add App Password**.
2. Fill in `BLUESKY_IDENTIFIER` (your handle, e.g. `you.bsky.social`, or the email on the account) and `BLUESKY_APP_PASSWORD`.
3. **Confirm the account's email** (Settings → Email) if you haven't already. Video upload specifically fails with a 401 `unconfirmed_email` otherwise — found by actually running this against a real account, not documented anywhere obvious up front.

`BLUESKY_SERVICE` is optional — only set it if you're on a self-hosted Personal Data Server instead of the default `bsky.social`.

Note: video posting on AT Protocol requires the video to finish server-side processing before it can be attached to a post — `BlueskyAdapter.upload()` handles the upload-then-poll flow internally, but it does mean a Bluesky post can take a little longer to go through than the other platforms.

## Pinterest

1. Create a Pinterest Developer app at https://developers.pinterest.com.
2. Run the OAuth flow yourself, granting `pins:write` and `boards:read`.
3. Find the target board's id (`GET /v5/boards`, or from the board's URL) and fill in `PINTEREST_ACCESS_TOKEN` and `PINTEREST_BOARD_ID`.

`PinterestAdapter.upload()` requires `VideoAsset.local_path` — it uploads the file directly and generates the required cover image itself (the video's own first frame) rather than needing you to host a separate thumbnail.

## LinkedIn and TikTok — via UploadPost.com

Both platforms are gated behind an approval process that isn't self-serve: LinkedIn requires applying for their Marketing/Community Management partner API, and TikTok requires a formal Content Posting API audit that can take weeks. Rather than go through either, both are routed through [UploadPost.com](https://upload-post.com), which already holds an approved app for each.

1. Create an UploadPost account and grab your API key from their dashboard.
2. In the UploadPost dashboard, click **Connect** for LinkedIn and/or TikTok and approve the permissions in the popup that opens — no app of your own to create, no waiting on either platform's review.
3. Fill in `UPLOADPOST_API_KEY` and `UPLOADPOST_USER` (the profile username shown in their dashboard once connected).

Note: `UploadPostAdapter.verify_live()` can only trust the upload response itself — UploadPost's docs don't expose a separate get-post/status endpoint, so this is a genuinely weaker live-confirmation guarantee than the native adapters, which always re-check the post via the platform's own API. Also note the endpoint/field names here were taken from UploadPost's docs but not exercised against a live account in this codebase — confirm against their current docs before relying on this in production.

Free tier: UploadPost's $0 plan excludes TikTok entirely and caps at 10 uploads/month. The Basic plan (~$16–24/mo) is needed for TikTok and unlimited uploads.

## Email notifications

Standard SMTP — `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`. Any provider works (Gmail app
password, SendGrid SMTP relay, etc.).

## Usage

```python
from pathlib import Path
from distribution_agent import distribute
from distribution_agent.adapters.base import VideoAsset

asset = VideoAsset(
    caption="Check out our new product!",
    local_path=Path("video.mp4"),      # needed for YouTube, Reddit, Bluesky, Pinterest, LinkedIn, TikTok
    public_url="https://cdn.example.com/video.mp4",  # needed for Instagram, optional for Facebook
)

records = distribute(asset, platforms=["youtube", "instagram"], poc_email="client@example.com")
for r in records:
    print(r)
```

Only pass videos here that have already passed the Quality Control
Agent (see `agent-prompts.md`).

### Approval gate

`distribute()` never posts without asking first. By default it prompts
on the terminal per platform (`Post "..." to instagram? [y/N]`) and
skips (`approved=False` in the returned record) on anything other than
an explicit yes — including when there's no terminal to prompt on at
all, so an unattended run can't accidentally post.

To wire approval to something other than a terminal prompt — a
dashboard button, a Slack confirmation — pass your own `approve`
callback: it receives `(platform, asset)` and must return `True` for
that platform's post to go out.

```python
def approve_from_dashboard(platform: str, asset) -> bool:
    return get_human_decision(platform, asset.caption)  # your own approval UI

records = distribute(asset, platforms=["youtube"], approve=approve_from_dashboard)
```
