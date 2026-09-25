---
name: higgsfield
description: Generate AI video (and image) ads and creative content through the Higgsfield API (api.higgsfield.ai) - text-to-video, image-to-video, motion transfer, and more, across model families like Seedance, Kling, Wan, Genjutsu, SOUL, and others. Use this skill whenever the user asks to generate, create, or produce a video ad, product video, marketing video, or AI-generated image/video content for Serfis or a Serfis lead/prospect, or mentions Higgsfield by name. Covers authentication, the async submit-then-poll request lifecycle, and - critically - how to look up the correct request schema for whichever specific model is being used, since it varies per model and must never be guessed or hardcoded.
---

# Higgsfield API

Higgsfield (api.higgsfield.ai) generates images and videos through model
endpoints (Seedance, Kling, Wan, Genjutsu, SOUL, Cinema Studio, and others).
Every model shares the same authentication and request lifecycle; the
request *body* is model-specific.

## The one rule that matters most: don't guess the request schema

The official docs are explicit about this: *"Endpoint fields vary by model
and workflow. Use the exact schema documented on the selected model page."*
Every model has its own page with its own required fields - some take a
`prompt`, some take `image_urls`, some take `video_url` + `image_urls`
(motion transfer), some take duration/resolution/aspect-ratio options that
differ model to model.

**Before generating anything with a model you haven't used in this
session:**
1. Go to https://console.higgsfield.ai to find the model and its
   documentation page (or ask the user which specific model/workflow they
   want - e.g. "Seedance 2.0 text-to-video" vs "Genjutsu motion transfer").
2. Fetch that model's own docs page for its exact request schema and
   example. Model pages live under `docs.higgsfield.ai/docs/models/...` -
   append `.md` to any docs URL to get a clean markdown version.
3. If you get stuck finding the right page, fetch
   `https://docs.higgsfield.ai/docs/llms.txt` first - it's an index of
   every doc page, written for exactly this purpose.
4. Only after confirming the real schema, build the request. Don't reuse a
   schema from a different model "because it's probably similar" - this
   burned real time and money on this project's Apify integration when a
   schema was assumed instead of confirmed; don't repeat that here.

This applies even if a model was already used earlier in the conversation -
docs can be checked once per model per session, not once per skill use.

## Authentication

Two separate credentials, not one: a **Key ID** and a **Key Secret**, sent
together in one header:

```
Authorization: Key <HF_API_KEY_ID>:<HF_API_KEY_SECRET>
```

They're stored in this project's `.env` as `HIGGSFIELD_API_KEY_ID` and
`HIGGSFIELD_API_KEY_SECRET`. Load them from there (e.g. via `python-dotenv`,
already a dependency in this project) - **never ask the user to paste
either value into chat.** If a key looks like it might already be exposed
in a terminal log or chat history, tell the user to rotate it in the
Higgsfield Console rather than continuing to use it.

## Request lifecycle

Every generation is async: submit, then poll (or use a webhook) for the
result.

**1. Submit** - `POST` to the model's endpoint:
```bash
curl --request POST \
  --url https://api.higgsfield.ai/<model-specific-path> \
  --header "Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}" \
  --header "Content-Type: application/json" \
  --data '{ ...model-specific body, confirmed from that model's docs page... }'
```

Immediate response:
```json
{
  "status": "queued",
  "request_id": "d7e6c0f3-...",
  "status_url": "https://api.higgsfield.ai/requests/d7e6c0f3-.../status",
  "cancel_url": "https://api.higgsfield.ai/requests/d7e6c0f3-.../cancel"
}
```

**2. Poll** `status_url` until it reaches a terminal state
(`completed` / `failed` / `nsfw` / `canceled`). Use
`scripts/poll_request.py` in this skill rather than re-writing the polling
loop by hand - it already implements Higgsfield's documented backoff
strategy (start at 2s, grow to 10s, add jitter) and the retry table below.

| Response | Action |
|---|---|
| `200` with a non-terminal status | keep polling with backoff |
| `401` | stop - credentials are wrong, don't retry |
| `404` | stop - check the request ID/account |
| `5xx` or network failure | retry the status check with backoff |

**3. Result** - a `completed` response includes the output URLs (e.g.
`videos: [{url: ...}]` or `images: [{url: ...}]` - field name depends on
the model, check its docs page). **Outputs are only hosted for 7 days** -
download and save anywhere it needs to persist (this project's convention
would be `output/` or a dedicated `content/` folder, not left on
Higgsfield's CDN).

## Input media (image-to-video, motion transfer, etc.)

Models that take reference images/video need **publicly accessible URLs**,
not local file paths. See `docs.higgsfield.ai/docs/concepts/file-uploads.md`
for uploading local files to Higgsfield's own storage first if there's no
other public URL to use (e.g. a lead's product image scraped from their
site would already have a public URL and can be used directly).

## Connecting this to the Serfis lead-gen pipeline

If the task is "make a video ad for/about a specific lead," pull that
lead's real data from the existing SQLite database (`storage.py` -
`get_lead(lead_id)`) for the prompt/reference material - company name,
what_they_sell, research_notes are already there. Don't invent product
details Higgsfield should show; ground the prompt in what the lead's own
research already contains, the same way outreach emails and reply drafts
already do.

This skill does not send or publish anything - it only generates a video
file. If the resulting video is meant to attach to outreach, treat that as
a separate, explicit step the human approves, consistent with how every
other outbound artifact in this project works.

## Reference

- `references/lifecycle.md` - full request lifecycle, error codes, rate
  limits, and billing/retention details in one place (condensed from the
  official docs, for when you don't want to re-fetch them)
- `scripts/poll_request.py` - reusable polling helper (submit still needs
  the model-specific body you confirm from that model's own docs page)
