"""One-time setup helper: generates a Pinterest OAuth access token.

Run this yourself, locally: `python get_pinterest_token.py`

Reads PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET from .env (fill
those in first, per SETUP.md — and make sure the app's redirect URI is
exactly http://localhost:8765/callback). It opens your browser for you
to log in and approve access, catches the redirect with a tiny local
server, exchanges the resulting code for an access token, then prints
that token here in your own terminal. Copy it into .env as
PINTEREST_ACCESS_TOKEN yourself — like the YouTube helper, this
deliberately isn't something Claude runs on your behalf, since the
whole point is producing a secret that should only ever appear in your
own terminal.

Note: Pinterest access tokens expire (historically ~30 days) and this
script doesn't yet handle refresh — PinterestAdapter uses a static
token today. Re-run this script to get a new one when it expires.
"""

import base64
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "http://localhost:8765/callback"
# Pinterest's OpenAPI spec lists these four for Create Pin (pins:read and pins:write
# are also listed for Register media upload). Trim later if a test shows fewer work.
# The *_secret scopes are needed to see and post to secret (private) boards.
SCOPES = "boards:read,boards:write,pins:read,pins:write,boards:read_secret,boards:write_secret,pins:read_secret,pins:write_secret"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env — fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    client_id = require("PINTEREST_CLIENT_ID")
    client_secret = require("PINTEREST_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)

    captured = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            captured["code"] = query.get("code", [None])[0]
            captured["state"] = query.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Done -- you can close this tab and return to your terminal.</body></html>")

        def log_message(self, *args):
            pass  # silence default request logging

    auth_url = "https://www.pinterest.com/oauth/?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
        }
    )

    print("Opening your browser -- log in and approve access, then come back here.")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.handle_request()  # blocks until the one redirect comes in

    if captured.get("state") != state:
        raise SystemExit("State mismatch -- possible tampering, or a stale browser tab. Try again.")
    if not captured.get("code"):
        raise SystemExit("No authorization code received. Check the redirect URI matches exactly, then try again.")

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_resp = requests.post(
        "https://api.pinterest.com/v5/oauth/token",
        headers={"Authorization": f"Basic {basic_auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": captured["code"], "redirect_uri": REDIRECT_URI},
        timeout=15,
    )
    token_resp.raise_for_status()
    body = token_resp.json()

    print("\nSuccess. Add this line to your .env yourself:\n")
    print(f"PINTEREST_ACCESS_TOKEN={body['access_token']}")
    if "refresh_token" in body:
        print(f"\n(A refresh_token was also issued, expires_in={body.get('expires_in')}s. Not currently used by PinterestAdapter, but worth saving somewhere if you want to add refresh support later.)")


if __name__ == "__main__":
    main()
