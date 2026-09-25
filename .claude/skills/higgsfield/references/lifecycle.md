# Higgsfield API - condensed reference

Full source: https://docs.higgsfield.ai/docs/llms.txt (fetch that page for
the complete, current index - this file is a snapshot, not a replacement
for checking a specific model's own docs page).

## Easiest path: official SDK

Higgsfield publishes an official Python client that handles submit + poll
in one call:

```python
import higgsfield_client

result = higgsfield_client.subscribe(
    "kling-video/v3.0/std/text-to-video",   # the model's Endpoint ID
    arguments={"prompt": "A slow cinematic tracking shot along a sunlit coastal road."},
)
print(result["video"]["url"])
```

The Endpoint ID is on the model's own docs page (e.g.
`kling-video/v3.0/std/text-to-video` for Kling 3.0 Standard text-to-video).
Check if `higgsfield_client` is already installed (`pip show higgsfield_client`)
before falling back to raw REST below - it's simpler and already implements
the retry/backoff behavior documented here.

## Raw REST, if the SDK isn't available

**Estimate cost first** (same body as the real request, no charge):
```bash
curl --request POST \
  --url https://api.higgsfield.ai/estimate/<endpoint-id> \
  --header "Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}" \
  --header "Content-Type: application/json" \
  --data '{ ...same body you plan to submit... }'
# -> {"credits": "1.500", "usd": "0.094"}
```

**Submit:**
```bash
curl --request POST \
  --url https://api.higgsfield.ai/<endpoint-id> \
  --header "Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}" \
  --header "Content-Type: application/json" \
  --data '{ ...model-specific body, confirmed from that model's docs page... }'
```
Returns `{"status": "queued", "request_id": "...", "status_url": "...", "cancel_url": "..."}`.

**Poll** `status_url` until terminal (`completed`/`failed`/`nsfw`/`canceled`)
- use `scripts/poll_request.py` rather than re-implementing this.

## Synchronous error codes

| Status | Meaning | Retry? |
|---|---|---|
| 400 | Invalid parameters, rejected input, or concurrency reached | After correcting/waiting |
| 401 | Missing or invalid credentials | No - fix credentials |
| 403 | Insufficient credits | After funding the account |
| 404 | Request or model not found for this account | No |
| 422 | Request body validation failed | No |
| 423 | Model temporarily blocked | Later |
| 500 | Unexpected server error | Yes, with backoff |
| 503 | Model disabled or not ready | Later |

`failed`/`nsfw` terminal results and successfully canceled queued requests
are **not charged** (reserved credits are refunded automatically).

## Retry policy

- Retry `GET` status checks after network failures / `5xx` - exponential
  backoff with jitter, a max attempt count, and a total deadline.
- Never retry auth/validation failures without changing the request.
- Never blindly re-`POST` a generation after an ambiguous timeout -
  submissions don't currently support an idempotency key, so a retry could
  create a second (billed) generation. Check the original request's status
  first if one was returned.
- Every response has an `X-Correlation-ID` header - log it alongside
  `request_id` if you need to ask Higgsfield support about a specific run.

## Output retention

Generated files are hosted for **at least 7 days**, then may be removed.
Download anything that needs to persist - don't leave it on Higgsfield's CDN
as the source of truth.

## Credits

Credits expire 1 year after being added to the account. Cost varies by
model/parameters - always check with the estimate endpoint above before a
generation the user hasn't explicitly approved the cost of, the same way
this project checks Apify Actor add-on costs before enabling them.
