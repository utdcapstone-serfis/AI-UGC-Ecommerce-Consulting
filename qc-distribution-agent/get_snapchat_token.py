"""One-time setup helper: generates Snapchat Public Profile API tokens.

Run this yourself, locally: `python get_snapchat_token.py`

Reads SNAPCHAT_CLIENT_ID and SNAPCHAT_CLIENT_SECRET from .env (fill those in first,
from the OAuth app in Business Manager, Business Details; not the Developer Portal).
The OAuth app's redirect address must be exactly the REDIRECT_URI below.

How it works:
  1. The script prints a Snapchat login link. Open it in a browser signed in to the
     shared team Snapchat account, and click Continue.
  2. Snap sends the browser to the redirect address (the page will probably show
     "404", which is expected). Copy the whole address from the browser's address bar
     (or just the value after code=) and paste it here.
  3. The script exchanges the code for an access token and a refresh token and prints
     them in your own terminal. Copy them into .env yourself. This is deliberately not
     something Claude runs for you, since it produces secrets.

Snap's guide says the access token lasts one hour (expires_in 3600), so the refresh
token is what the app will keep using. The Public Profile API is allowlist-only: a token
may be issued before Snap allowlists the client ID, but the API calls can still be refused.
"""

import os
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://accounts.snapchat.com/login/oauth2/authorize"
TOKEN_URL = "https://accounts.snapchat.com/login/oauth2/access_token"
REDIRECT_URI = "https://utdcapstone-serfis.github.io/serfis-site/callback"
SCOPE = "snapchat-profile-api"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env. Fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    client_id = require("SNAPCHAT_CLIENT_ID")
    client_secret = require("SNAPCHAT_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)

    link = AUTH_URL + "?" + urlencode(
        {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI, "scope": SCOPE, "state": state}
    )
    print("1. Open this link in a browser signed in to the shared team Snapchat account, then click Continue:\n")
    print(link)
    print("\n2. The browser then goes to the redirect address (a 404 page is fine).")
    print("   Copy the whole address from the address bar, or just the code= value, and paste it below.\n")
    pasted = input("Paste here: ").strip().strip('"')
    if not pasted:
        raise SystemExit("Nothing pasted. Run the script again.")

    code = pasted
    if "code=" in pasted or pasted.startswith("http"):
        query = parse_qs(urlparse(pasted).query)
        code = (query.get("code") or [""])[0]
        returned_state = (query.get("state") or [""])[0]
        if returned_state and returned_state != state:
            raise SystemExit("State mismatch: this code is from a different login link. Use the link printed above, then try again.")
        if not code:
            error = (query.get("error_description") or query.get("error") or ["no code found"])[0]
            raise SystemExit(f"Snapchat did not return a code ({error}).")

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=20,
    )
    if not resp.ok:
        # Never echo the request (it holds the secret); the response is safe to show.
        raise SystemExit(f"Token request failed (HTTP {resp.status_code}): {resp.text[:300]}\nCodes expire quickly; get a new one and rerun.")
    body = resp.json()

    print("\nSuccess. Add these lines to your .env yourself:\n")
    print(f"SNAPCHAT_ACCESS_TOKEN={body['access_token']}")
    if body.get("refresh_token"):
        print(f"SNAPCHAT_REFRESH_TOKEN={body['refresh_token']}")
    print(f"\n(Scope: {body.get('scope')}. The access token lasts about {int(body.get('expires_in', 0)) // 60} minutes; the refresh token renews it.)")


if __name__ == "__main__":
    main()
