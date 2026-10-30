"""
Configuration for the CommandIA AI layer.

Loads the Gemini API key / model settings and the conversational AI tuning
constants used by the brain (retries, guardrails thresholds, supported
dialects).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

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
# Upper bound for a single wait. The Gemini free tier answers 429 with the
# delay it expects ("Please retry in 15.5s"), and that delay is used when it
# is longer than the exponential backoff.
RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "60"))
CONFIRMATION_THRESHOLD = 5  # 5 sacred fields

# Allowed languages/dialects as per PRD
SUPPORTED_LANGUAGES = ["darija", "franco_arabic", "french", "english"]
