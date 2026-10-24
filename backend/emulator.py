import requests
import time
import json

# Your local FastAPI webhook endpoint
WEBHOOK_URL = "http://127.0.0.1:8000/webhook"

# A realistic Instagram DM webhook payload
# We are using a Darija/Franco-Arabic test message for the Golden Dataset
payload = {
    "object": "instagram",
    "entry": [
        {
            "id": "123456789_BROWNIES_MAHELMA_ID", # Your Instagram Business Account ID
            "time": int(time.time()),
            "messaging": [
                {
                    "sender": {
                        "id": "987654321_CUSTOMER_ID" # The customer's scoped ID
                    },
                    "recipient": {
                        "id": "123456789_BROWNIES_MAHELMA_ID"
                    },
                    "timestamp": int(time.time()),
                    "message": {
                        "mid": "m_wZ2...", # Unique message ID
                        "text": "Salam, nhab ncomandi 2 boites de brownies classiques l Alger centre, home delivery. Mon num c'est 0555123456"
                    }
                }
            ]
        }
    ]
}

print(f"🚀 Sending simulated Instagram DM to {WEBHOOK_URL}...")

try:
    # Send the POST request to your FastAPI server
    response = requests.post(WEBHOOK_URL, json=payload)
    
    print(f"✅ Status Code: {response.status_code}")
    print(f"📥 Server Response: {response.text}")
    
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is your FastAPI server running? (Run: uvicorn main:app --reload)")