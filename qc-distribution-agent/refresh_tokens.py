"""Refreshes the credentials that expire, so they don't lapse between posts.

Run: `python refresh_tokens.py`

Instagram's token lasts 60 days and TikTok's access token 24 hours; adapters
refresh them when one is created, but nothing refreshes them during a long gap
with no posts, so run this at least every 30 days (X's refresh token also
lapses after about 6 months unused). It prints only a status line per
platform, never a token. Rotated tokens are saved into .env, or parked in a
gitignored `*.pending` file with a warning if .env can't be written.

Platforms not listed here need no refresh (Facebook Page token, Bluesky app
password, YouTube refresh token) or can't be refreshed by code (LinkedIn).
"""

import warnings

import distribution_agent  # noqa: F401  (loads .env)
from distribution_agent.config import ConfigError


def run(name, refresh):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = refresh()
        except ConfigError:
            print(f"{name:10} not configured (missing env vars) - skipped")
            return
        except Exception as exc:  # type only: messages can contain request details
            print(f"{name:10} ERROR ({type(exc).__name__})")
            return
    print(f"{name:10} {result}")
    for warning in caught:
        print(f"           note: {warning.message}")


def instagram():
    from distribution_agent.adapters.instagram import InstagramAdapter

    adapter = InstagramAdapter(auto_refresh=False)
    return "refreshed" if adapter.refresh_credentials(force=True) else "not refreshed (see note)"


def tiktok():
    from distribution_agent.adapters.tiktok import TikTokAdapter

    adapter = TikTokAdapter(auto_refresh=False)
    return "refreshed" if adapter.refresh_credentials() else "not refreshed (see note, or no TIKTOK_REFRESH_TOKEN set)"


def x():
    from distribution_agent.adapters.x import XAdapter

    XAdapter()._get_access_token()
    return "refreshed"


if __name__ == "__main__":
    run("Instagram", instagram)
    run("TikTok", tiktok)
    run("X", x)
