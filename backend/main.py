import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

# Locate and load .env file
env_path = find_dotenv()
load_dotenv(env_path, override=True)

META_VERIFY_TOKEN = (os.getenv("META_VERIFY_TOKEN") or "LlllDiyacWWoha20nvso42lqwpLNsfsL8n3sna3azp")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") 

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="CommandIA Webhook API")

def create_mock_order(customer_id: str, original_message: str):
    # This JSON structure now strictly matches the columns in schema.sql
    mock_order_data = {
        "customer_name": "Fadoua Test",
        "phone_number": "0555123456", 
        "wilaya_code": 16,
        "wilaya_name": "Alger",
        "delivery_type": "HOME",
        "address": "Alger Centre, near La Grande Poste",
        "subtotal_da": 3100.00,
        "shipping_fee_da": 600.00,
        "total_price_da": 3700.00,
        "status": "PENDING_CONFIRMATION"
    }
    
    try:
        # 1. Insert the main order into the 'orders' table
        order_response = supabase.table("orders").insert(mock_order_data).execute()
        new_order_id = order_response.data[0]['id']
        print(f"✅ Order successfully saved to Supabase! Order ID: {new_order_id}")
        
        # 2. Insert the specific brownies into the 'order_items' table
        mock_item_data = {
            "order_id": new_order_id,
            "extracted_product_name": "Brownie Classique",
            "quantity": 2,
            "unit_price_da": 1550.00
        }
        supabase.table("order_items").insert(mock_item_data).execute()
        print(f"✅ Order items successfully linked to Order ID: {new_order_id}")
        
    except Exception as e:
        print(f"❌ Database Insert Error: {e}")

# Database Read Function (For AI Tool Calling)
def check_inventory(product_id: str):
    print(f"🔍 AI is checking inventory for product ID: {product_id}...")
    try:
        # Query the 'products' table for this specific item
        response = supabase.table("products").select("stock_quantity, name").eq("id", product_id).execute()
        
        # If the product exists, return the exact quantity to the AI
        if response.data:
            stock = response.data[0]['stock_quantity']
            product_name = response.data[0]['name']
            print(f"📦 Inventory Result: {stock} {product_name}(s) available.")
            return stock
        else:
            print("❌ Product not found in database.")
            return 0
            
    except Exception as e:
        print(f"❌ Database Read Error: {e}")
        return 0

@app.get("/")
def read_root():
    return {"status": "CommandIA API is running"}

# GET route for Meta's initial verification handshake
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        print("✅ WEBHOOK HANDSHAKE VERIFIED!")
        return PlainTextResponse(content=challenge)

    raise HTTPException(status_code=403, detail="Verification token mismatch")

# POST route to capture incoming Instagram DMs
@app.post("/webhook")
async def handle_instagram_webhook(request: Request):
    # 1. Grab the JSON data sent by your emulator
    payload = await request.json()
    
    try:
        # 2. Verify it's an Instagram webhook
        if payload.get("object") == "instagram":
            
            # 3. Dig into the nested structure Meta uses
            for entry in payload.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    
                    # 4. Extract the exact pieces of data the AI needs
                    sender_id = messaging_event.get("sender", {}).get("id")
                    message_text = messaging_event.get("message", {}).get("text")
                    
                    # 5. If there is text, print it!
                    if message_text:
                        print("\n" + "="*50)
                        print(f"📩 NEW MESSAGE RECEIVED!")
                        print(f"👤 Customer ID: {sender_id}")
                        print(f"💬 Message: {message_text}")
                        
                        # 6. Trigger the database write
                        print("⚙️ Simulating AI processing and saving to database...")
                        create_mock_order(sender_id, message_text)
                        
                        print("="*50 + "\n")

        # Always return a 200 OK success to Meta/Emulator
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Error parsing webhook: {e}")
        return {"status": "error"}