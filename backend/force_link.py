import urllib.request
import urllib.parse
import json

# 1. Replace this exact string with the long access token you generated earlier
ACCESS_TOKEN = "LlllDiyacWWoha20nvso42lqwpLNsfsL8n3sna3azp"


url = "https://graph.facebook.com/v21.0/me/subscribed_apps"
data = urllib.parse.urlencode({
    "subscribed_fields": "messages",
    "access_token": ACCESS_TOKEN
}).encode('utf-8')

req = urllib.request.Request(url, data=data, method='POST')

print("Sending subscription request to Meta...")

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print("✅ Meta API Response:", result)
except urllib.error.HTTPError as e:
    print("❌ Meta API Error:", e.read().decode())