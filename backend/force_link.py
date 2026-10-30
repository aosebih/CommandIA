"""Subscribe the Page to the messaging webhook field. Token comes from .env."""
import json
import os
import urllib.parse
import urllib.request

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
if not ACCESS_TOKEN or ACCESS_TOKEN.startswith("your_"):
    raise SystemExit("Set META_ACCESS_TOKEN in .env before subscribing the app.")

GRAPH_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")
url = f"https://graph.facebook.com/{GRAPH_VERSION}/me/subscribed_apps"
data = urllib.parse.urlencode({
    "subscribed_fields": "messages",
    "access_token": ACCESS_TOKEN,
}).encode("utf-8")

req = urllib.request.Request(url, data=data, method="POST")
print("Sending subscription request to Meta...")
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print("Meta API response:", result)
except urllib.error.HTTPError as error:
    print("Meta API error:", error.read().decode())
