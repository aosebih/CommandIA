"""
Configuration for CommandIA AI module.
Loads Gemini API key and model settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Conversation settings
MAX_RETRIES = 3
CONFIRMATION_THRESHOLD = 5  # 5 sacred fields

# Allowed languages/dialects as per PRD
SUPPORTED_LANGUAGES = ["darija", "franco_arabic", "french", "english"]
