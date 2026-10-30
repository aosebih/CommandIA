"""Read merchants through the REST API using credentials from .env."""
import os

from dotenv import load_dotenv

from backend.supabase_client import SupabaseRest

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if not url or not key or url.startswith("your_"):
    raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env")

client = SupabaseRest(url, key)
print("Merchants:", client.get("merchants", {"select": "*"}))
