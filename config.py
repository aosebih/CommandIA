"""
Configuration for CommandIA AI module.
Loads Gemini API key and model settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


def is_configured(value: str | None) -> bool:
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

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Primary model. gemini-2.5-flash returns 404 for new API keys
# ("no longer available to new users"), so the default is a 3.x model.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Tried in order when the primary model fails with a transient error.
GEMINI_MODEL_FALLBACKS = [
    model.strip()
    for model in os.getenv("GEMINI_MODEL_FALLBACKS", "gemini-3.5-flash").split(",")
    if model.strip()
]

# Conversation settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "2.0"))
CONFIRMATION_THRESHOLD = 5  # 5 sacred fields

# Allowed languages/dialects as per PRD
SUPPORTED_LANGUAGES = ["darija", "franco_arabic", "french", "english"]

# Meta Graph API (Instagram / Facebook DMs)
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_PAGE_ID = os.getenv("META_PAGE_ID")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")

META_ENABLED = is_configured(META_ACCESS_TOKEN)

# Service configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
COMMANDIA_API_KEY = os.getenv("COMMANDIA_API_KEY")

# Supabase persistence (optional: disabled when credentials are absent)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_ORDERS_TABLE = os.getenv("SUPABASE_ORDERS_TABLE", "orders")

SUPABASE_ENABLED = is_configured(SUPABASE_URL) and is_configured(SUPABASE_KEY)
