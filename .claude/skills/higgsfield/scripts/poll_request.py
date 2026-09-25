"""Reusable Higgsfield request-status poller.

Implements the exact backoff strategy documented at
https://docs.higgsfield.ai/docs/concepts/polling.md - this handles the
generic "wait for a request to finish" part that's identical across every
model. Submitting the generation itself is NOT here, since the request body
is model-specific - confirm that from the model's own docs page first (see
SKILL.md), then call poll_request() with the status_url you get back.

Usage:
    from poll_request import poll_request
    result = poll_request(status_url, key_id, key_secret)
    if result["status"] == "completed":
        print(result["video"]["url"])  # or result["images"][0]["url"], etc.
"""
import random
import time

import requests

TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}


def poll_request(status_url: str, key_id: str, key_secret: str,
                  timeout_seconds: int = 600) -> dict:
    """Blocks until the request reaches a terminal state or timeout_seconds
    elapses. Returns the final status response dict.

    Raises TimeoutError if the request never reaches a terminal state within
    timeout_seconds - pick a timeout appropriate for the model (video
    generation can reasonably take several minutes).
    """
    headers = {"Authorization": f"Key {key_id}:{key_secret}"}
    delay = 2.0
    start = time.time()

    while True:
        if time.time() - start > timeout_seconds:
            raise TimeoutError(
                f"Request did not reach a terminal state within {timeout_seconds}s: {status_url}"
            )

        resp = requests.get(status_url, headers=headers, timeout=30)

        if resp.status_code == 401:
            raise PermissionError("Invalid Higgsfield credentials - do not retry, fix them first.")
        if resp.status_code == 404:
            raise LookupError(f"Request not found: {status_url}")
        if resp.status_code >= 500:
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 1.5, 10.0)
            continue

        resp.raise_for_status()
        result = resp.json()

        if result.get("status") in TERMINAL_STATUSES:
            return result

        time.sleep(delay + random.uniform(0, 0.5))
        delay = min(delay * 1.5, 10.0)
