"""One-time setup helper: generates a TikTok OAuth access token.

Run this yourself, locally: `python get_tiktok_token.py`

Reads TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET from .env (fill those
in first, per SETUP.md — use the Sandbox app's own Client key/secret
while testing, not Production's, since Production isn't approved yet).

Unlike the YouTube/Pinterest/X helpers, this can't catch the redirect
with a local server — TikTok rejects `localhost` as a redirect URI
entirely (even in Sandbox), so the app is configured to redirect to
https://utdcapstone-serfis.github.io/serfis-site/callback/ instead, a
static page that just displays whatever's in the URL for you to copy.
Opens your browser for you to log in and approve access (make sure
you're approving against a Sandbox Target User, not your main account),
then pauses here for you to paste the `code` value shown on that page.
Exchanges it for a token and prints it in your own terminal — copy it
into .env as TIKTOK_ACCESS_TOKEN yourself, same reasoning as every
other helper here: the output is a secret, so it should only ever
appear in your own terminal, not something Claude runs for you.
"""

import os
import secrets
import webbrowser
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "https://utdcapstone-serfis.github.io/serfis-site/callback/"
SCOPES = "user.info.basic,video.publish,video.upload"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env — fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    client_key = require("TIKTOK_CLIENT_KEY")
    client_secret = require("TIKTOK_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)

    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(
        {
            "client_key": client_key,
            "scope": SCOPES,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "state": state,
        }
    )

    print("Opening your browser -- log in and approve access as the Sandbox Target User you added, then come back here.")
    webbrowser.open(auth_url)

    print("\nAfter approving, you'll land on the callback page showing the values TikTok sent back.")
    code = input("Paste the 'code' value shown on that page here: ").strip()
    returned_state = input("Paste the 'state' value shown on that page here: ").strip()

    if returned_state != state:
        raise SystemExit("State mismatch -- possible tampering, or a stale browser tab. Try again.")
    if not code:
        raise SystemExit("No authorization code provided.")

    token_resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    token_resp.raise_for_status()
    body = token_resp.json()

    print("\nSuccess. Add these lines to your .env yourself:\n")
    print(f"TIKTOK_ACCESS_TOKEN={body['access_token']}")
    if body.get("refresh_token"):
        print(f"TIKTOK_REFRESH_TOKEN={body['refresh_token']}")


if __name__ == "__main__":
    main()
