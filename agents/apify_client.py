"""Thin wrapper around Apify's REST API so every agent calls it the same way.

Apify actors are run via a single synchronous endpoint that starts the actor,
waits for it to finish, and returns its output dataset directly - no separate
polling loop needed for actors that finish within the request timeout.
Docs: https://docs.apify.com/api/v2/act-run-sync-get-dataset-items-post
"""
from typing import Optional

import requests

import config

BASE_URL = "https://api.apify.com/v2"


def run_actor(actor_id: str, run_input: dict, timeout: int = 120,
              max_charge_usd: Optional[float] = None) -> list[dict]:
    """Runs an Apify Actor synchronously and returns its output dataset items.

    `actor_id` uses Apify's URL form, e.g. "vdrmota/contact-info-scraper" -
    the "/" is converted to "~" here since that's what the API endpoint needs.
    `max_charge_usd` is a hard cap Apify enforces on pay-per-event Actors: the
    run stops charging past it. The token goes in a header, not the URL, so it
    can't leak into an error message. Raises requests.HTTPError on failure -
    callers should catch it.
    """
    slug = actor_id.replace("/", "~")
    url = f"{BASE_URL}/acts/{slug}/run-sync-get-dataset-items"
    params = {"maxTotalChargeUsd": max_charge_usd} if max_charge_usd else {}
    headers = {"Authorization": f"Bearer {config.APIFY_API_TOKEN}"}
    resp = requests.post(url, params=params, headers=headers, json=run_input, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
