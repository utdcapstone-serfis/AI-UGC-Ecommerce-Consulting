"""One-time setup helper: generates a YouTube OAuth refresh token.

Run this yourself, locally: `python get_youtube_token.py`

It reads YT_CLIENT_ID and YT_CLIENT_SECRET from .env (fill those in
first, per SETUP.md), opens your browser for you to log in and approve
access, then prints a refresh token here in your own terminal. Copy
that value into .env as YT_REFRESH_TOKEN yourself — this script
deliberately isn't something Claude runs on your behalf, since the
whole point of running it is to produce a secret, and that secret
should only ever appear in your own terminal, never in chat.
"""

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

import os

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name} in .env — fill it in first, per SETUP.md, then rerun this script.")
    return value


def main() -> None:
    client_config = {
        "installed": {
            "client_id": require("YT_CLIENT_ID"),
            "client_secret": require("YT_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print("Opening your browser — log in and approve access, then come back here.")
    credentials = flow.run_local_server(port=0)

    print("\nSuccess. Add this line to your .env yourself:\n")
    print(f"YT_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
