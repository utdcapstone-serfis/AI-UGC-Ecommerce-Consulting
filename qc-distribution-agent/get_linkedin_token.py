"""One-time setup helper: generates a LinkedIn OAuth access token.

Run this yourself, locally: `python get_linkedin_token.py`

Reads LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET from .env (fill those
in first, per SETUP.md, and make sure the app's authorized redirect URL is
exactly http://localhost:8765/callback). It opens your browser for you to
log in and approve access, catches the redirect with a tiny local server,
exchanges the code for an access token, and prints the token here in your
own terminal. Copy it into .env as LINKEDIN_ACCESS_TOKEN yourself; like the
other helpers, this deliberately isn't something Claude runs for you.

Scope: w_member_social (from the "Share on LinkedIn" product), which lets
the app post as the member who approves it.

Your member ID (LINKEDIN_PERSON_ID) comes from LinkedIn's OpenID Connect
userinfo call. That needs the "Sign In with LinkedIn using OpenID Connect"
product added to the app. If you have it, run:

    python get_linkedin_token.py --with-openid

and the script also prints your member ID. Without that product, leave the
flag off, or LinkedIn will refuse the login with an invalid-scope error.

Note: access tokens last about 60 days (the app's Auth tab shows the exact
duration) and this script doesn't handle refresh. Re-run it to get a new one.
"""

import argparse
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "http://localhost:8765/callback"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env. Fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-openid",
        action="store_true",
        help='also ask for openid+profile and print your member ID (needs the "Sign In with LinkedIn using OpenID Connect" product)',
    )
    args = parser.parse_args()

    client_id = require("LINKEDIN_CLIENT_ID")
    client_secret = require("LINKEDIN_CLIENT_SECRET")
    scopes = "w_member_social" + (" openid profile" if args.with_openid else "")
    state = secrets.token_urlsafe(16)

    captured = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            captured["code"] = query.get("code", [None])[0]
            captured["state"] = query.get("state", [None])[0]
            captured["error"] = query.get("error_description", query.get("error", [None]))[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Done -- you can close this tab and return to your terminal.</body></html>")

        def log_message(self, *args):
            pass  # silence default request logging

    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "scope": scopes,
        }
    )

    print(f"Asking for: {scopes}")
    print("Opening your browser -- log in and approve access, then come back here.")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.handle_request()  # blocks until the one redirect comes in

    if captured.get("error"):
        raise SystemExit(f"LinkedIn refused the login: {captured['error']}")
    if captured.get("state") != state:
        raise SystemExit("State mismatch -- possible tampering, or a stale browser tab. Try again.")
    if not captured.get("code"):
        raise SystemExit("No authorization code received. Check the redirect URL matches exactly, then try again.")

    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": captured["code"],
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    if not token_resp.ok:
        raise SystemExit(f"Token request failed (HTTP {token_resp.status_code}): {token_resp.text[:300]}")
    body = token_resp.json()
    access_token = body["access_token"]

    print("\nSuccess. Add this line to your .env yourself:\n")
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    print(f"\n(Expires in about {int(body.get('expires_in', 0)) // 86400} days.)")

    if args.with_openid:
        info = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if info.ok and info.json().get("sub"):
            print("\nYour member ID (not a secret). Add this line to your .env yourself:\n")
            print(f"LINKEDIN_PERSON_ID={info.json()['sub']}")
        else:
            print(f"\nCould not read your member ID (HTTP {info.status_code}). The token above is still valid.")


if __name__ == "__main__":
    main()
