"""Thin wrapper around Apify's REST API so every agent calls it the same way.

Apify actors are run via a single synchronous endpoint that starts the actor,
waits for it to finish, and returns its output dataset directly - no separate
polling loop needed for actors that finish within the request timeout.
Docs: https://docs.apify.com/api/v2/act-run-sync-get-dataset-items-post
"""
import requests

import config

BASE_URL = "https://api.apify.com/v2"


def run_actor(actor_id: str, run_input: dict, timeout: int = 120) -> list[dict]:
    """Runs an Apify Actor synchronously and returns its output dataset items.

    `actor_id` uses Apify's URL form, e.g. "vdrmota/contact-info-scraper" -
    the "/" is converted to "~" here since that's what the API endpoint needs.
    Raises requests.HTTPError on failure - callers should catch that the same
    way the Apollo/Hunter calls do.
    """
    slug = actor_id.replace("/", "~")
    url = f"{BASE_URL}/acts/{slug}/run-sync-get-dataset-items"
    params = {"token": config.APIFY_API_TOKEN}
    resp = requests.post(url, params=params, json=run_input, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
