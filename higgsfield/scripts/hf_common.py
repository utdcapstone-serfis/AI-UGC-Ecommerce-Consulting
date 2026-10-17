"""Shared helpers for the Higgsfield generation scripts in this folder.

Credentials come from the repo-root .env (HIGGSFIELD_API_KEY_ID / HIGGSFIELD_API_KEY_SECRET).
Every generation bills real money, so each script submits exactly one request and saves its
request id; if polling times out, re-run with `resume` to collect the SAME request instead of
paying for a new one.

Requires: pip install python-dotenv requests (imageio-ffmpeg for combine_clips.py / extend script)
"""
import json
import os
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "higgsfield" / "scripts"))
from poll_request import poll_request  # noqa: E402  (the skill's documented polling backoff)

load_dotenv(ROOT / ".env")
KID, KSEC = os.environ["HIGGSFIELD_API_KEY_ID"], os.environ["HIGGSFIELD_API_KEY_SECRET"]
AUTH = {"Authorization": f"Key {KID}:{KSEC}"}
API = "https://api.higgsfield.ai"
RUNS = ROOT / "higgsfield" / "runs"
RUNS.mkdir(parents=True, exist_ok=True)


def upload(path, content_type):
    """Upload a local file to a presigned URL; returns the public URL a model can read."""
    r = requests.post(f"{API}/files/generate-upload-url", headers={**AUTH, "Content-Type": "application/json"},
                      json={"content_type": content_type}, timeout=30)
    r.raise_for_status()
    u = r.json()
    with open(path, "rb") as f:   # send ONLY the returned headers; never the API credentials, to the storage URL
        requests.put(u["upload_url"], data=f, headers=u["upload_headers"], timeout=120).raise_for_status()
    return u["public_url"]


def submit(endpoint, body, run_name):
    r = requests.post(f"{API}/{endpoint}", headers={**AUTH, "Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
                      json=body, timeout=60)
    if not r.ok:
        print(r.text[:500])
    r.raise_for_status()
    sub = r.json()
    (RUNS / f"{run_name}.txt").write_text(sub["request_id"])
    print("submitted", sub["request_id"])
    return sub["status_url"]


def collect(status_url, out_path, kind):
    """Poll to completion and download the output ('images' or 'video')."""
    res = poll_request(status_url, KID, KSEC, timeout_seconds=540)
    print("status:", res["status"])
    if res["status"] != "completed":
        print(json.dumps({k: v for k, v in res.items() if k not in ("images", "video")}, indent=1)[:600])
        return None
    url = res["images"][0]["url"] if kind == "images" else res["video"]["url"]
    data = requests.get(url, timeout=180)
    data.raise_for_status()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(data.content)
    print("saved", out_path, len(data.content) // 1024, "KB")
    return out_path


def resume(run_name, out_path, kind):
    rid = (RUNS / f"{run_name}.txt").read_text().strip()
    return collect(f"{API}/requests/{rid}/status", out_path, kind)


def wants_resume():
    return len(sys.argv) > 1 and sys.argv[1] == "resume"
