"""One-time setup helper: generates an X (Twitter) OAuth refresh token.

Run this yourself, locally: `python get_x_token.py`

Reads X_CLIENT_ID and X_CLIENT_SECRET from .env (fill those in first,
per SETUP.md, and make sure the app's callback URL is exactly
http://localhost:8766/callback). Uses OAuth 2.0 Authorization Code
with PKCE. Opens your browser for you to log in and approve access,
catches the redirect with a tiny local server, exchanges the code for
tokens, then prints the refresh token here in your own terminal. Copy
it into .env as X_REFRESH_TOKEN yourself — same reasoning as the
YouTube/Pinterest helpers: the output is a secret, so it should only
ever appear in your own terminal, not something Claude runs for you.
"""

import base64
import hashlib
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "http://localhost:8766/callback"
SCOPES = "tweet.write tweet.read users.read media.write offline.access"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env — fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    client_id = require("X_CLIENT_ID")
    client_secret = require("X_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)

    code_verifier = secrets.token_urlsafe(64)[:128]
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")

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
            pass

    auth_url = "https://x.com/i/oauth2/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )

    print("Opening your browser -- log in and approve access, then come back here.")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8766), CallbackHandler)
    server.handle_request()

    if captured.get("state") != state:
        raise SystemExit("State mismatch -- possible tampering, or a stale browser tab. Try again.")
    if not captured.get("code"):
        raise SystemExit("No authorization code received. Check the callback URL matches exactly, then try again.")

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_resp = requests.post(
        "https://api.x.com/2/oauth2/token",
        headers={"Authorization": f"Basic {basic_auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": captured["code"],
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    token_resp.raise_for_status()
    body = token_resp.json()

    print("\nSuccess. Add this line to your .env yourself:\n")
    print(f"X_REFRESH_TOKEN={body['refresh_token']}")


if __name__ == "__main__":
    main()
