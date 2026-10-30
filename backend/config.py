"""
Configuration for the CommandIA backend service.

Loads the Meta Graph API, Supabase persistence and service settings used by
the FastAPI app, dashboard API and stores.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


def is_configured(value):
    """
    Return True when an environment value is a real credential.

    The shipped .env template keeps placeholder values such as
    "your_supabase_url_here". Treating those as configured would make the
    webhook and the Supabase writer fail against fake endpoints, so any
    service relying on a credential must check it first.
    """
    if not value:
        return False
    stripped = value.strip().strip("'\"").lower()
    if not stripped:
        return False
    return not (stripped.startswith("your_") and stripped.endswith("_here"))


# Meta Graph API (Instagram / Facebook DMs)
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PAGE_ID = os.getenv("META_PAGE_ID")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")
META_ENABLED = is_configured(META_ACCESS_TOKEN)

# Supabase persistence (optional: disabled when credentials are absent)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_ORDERS_TABLE = os.getenv("SUPABASE_ORDERS_TABLE", "orders")
SUPABASE_ORDER_ITEMS_TABLE = os.getenv("SUPABASE_ORDER_ITEMS_TABLE", "order_items")
SUPABASE_CONVERSATIONS_TABLE = os.getenv("SUPABASE_CONVERSATIONS_TABLE", "conversations")
SUPABASE_MESSAGES_TABLE = os.getenv("SUPABASE_MESSAGES_TABLE", "messages")
SUPABASE_PRODUCTS_TABLE = os.getenv("SUPABASE_PRODUCTS_TABLE", "products")
SUPABASE_MERCHANTS_TABLE = os.getenv("SUPABASE_MERCHANTS_TABLE", "merchants")
SUPABASE_SHIPPING_TABLE = os.getenv("SUPABASE_SHIPPING_TABLE", "shipping_rates")
SUPABASE_ENABLED = is_configured(SUPABASE_URL) and is_configured(SUPABASE_KEY)

# Service configuration
DEFAULT_MERCHANT_ID = os.getenv("DEFAULT_MERCHANT_ID")
DASHBOARD_ORIGIN = os.getenv("DASHBOARD_ORIGIN", "http://localhost:3000")
COMMANDIA_API_KEY = os.getenv("COMMANDIA_API_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
