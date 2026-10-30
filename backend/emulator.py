"""
Signed Instagram webhook emulator.

Hits the canonical FastAPI app (backend.app), not backend.main.
Usage:
    uvicorn backend.app:app --port 8000
    python -m backend.emulator
"""
import hashlib
import hmac
import json
import os
import time

import requests
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://127.0.0.1:8000/webhook")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")

payload = {
    "object": "instagram",
    "entry": [
        {
            "id": os.getenv("META_PAGE_ID", "123456789_BROWNIES_MAHELMA_ID"),
            "time": int(time.time()),
            "messaging": [
                {
                    "sender": {"id": "987654321_CUSTOMER_ID"},
                    "recipient": {
                        "id": os.getenv("META_PAGE_ID", "123456789_BROWNIES_MAHELMA_ID")
                    },
                    "timestamp": int(time.time() * 1000),
                    "message": {
                        "mid": f"m_emulator_{int(time.time())}",
                        "text": (
                            "Salam, nhab ncomandi 2 boites de brownies classiques "
                            "l Alger centre, home delivery. Mon num c'est 0555123456"
                        ),
                    },
                }
            ],
        }
    ],
}

raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
headers = {"Content-Type": "application/json"}
if META_APP_SECRET and not META_APP_SECRET.startswith("your_"):
    digest = hmac.new(META_APP_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    headers["X-Hub-Signature-256"] = f"sha256={digest}"
else:
    print("META_APP_SECRET is not configured; the real webhook will reject this request.")

print(f"Sending signed Instagram DM to {WEBHOOK_URL}...")
try:
    response = requests.post(WEBHOOK_URL, data=raw, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except requests.exceptions.ConnectionError:
    print("Connection error: start the API with `uvicorn backend.app:app --port 8000`")
